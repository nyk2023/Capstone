#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from control_msgs.action import GripperCommand
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, Constraints, PositionConstraint, BoundingVolume
from geometry_msgs.msg import PoseStamped, Point
from shape_msgs.msg import SolidPrimitive

class MoveItPoseClient(Node):
    def __init__(self):
        super().__init__('moveit_pose_client')
        
        # 1. MoveIt 핵심 액션 클라이언트 연결
        self._action_client = ActionClient(self, MoveGroup, 'move_action')
        self._gripper_clinet = ActionClient(self, GripperCommand, 'gripper_controller/gripper_cmd')
        
        # 2. 카메라 좌표 수신을 위한 토픽 구독
        self.subscription = self.create_subscription(
            Point,
            '/robot_tf',
            self.robot_tf_callback,
            10
        )
        
        # 🎯 [상태 관리 변수 도입]
        self.state = 'IDLE' 
        self.get_logger().info('📡 [정상 등록] /robot_tf 토픽 신호를 기다리는 중입니다...')
    
    def send_gripper_goal(self, position):
        self.get_logger().info('🤖 GripperCommand 액션 서버 연결 확인 중...')
        if not self._gripper_clinet.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('❌ GripperCommand 서버를 찾을 수 없습니다!')
            return
        
        goal_msg = GripperCommand.Goal()
        goal_msg.command.position = position
        goal_msg.command.max_effort = 10.0
        
        self.get_logger().info(f'📦 그리퍼 목표 전송 중... (위치: {position}m)')
        self._gripper_goal_future = self._gripper_clinet.send_goal_async(goal_msg)
        self._gripper_goal_future.add_done_callback(self.gripper_response_callback)

    def gripper_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('❌ 그리퍼가 명령을 거절했습니다.')
            # 에러 시 상태 초기화
            self.state = 'IDLE'
            return
        
        self.get_logger().info('✅ 그리퍼가 명령을 수락했습니다. 움직이기 시작합니다.')
        self._gripper_result_future = goal_handle.get_result_async()
        self._gripper_result_future.add_done_callback(self.get_gripper_result_callback)

    def get_gripper_result_callback(self, future):
        """ 🎯 그리퍼 구동이 완전히 끝났을 때 불리는 콜백 함수 """
        result = future.result().result
        self.get_logger().info('🏁 그리퍼 동작 완료.')

        # [분기점 1] 물건 집기(그리퍼 닫기)가 끝난 상황이라면?
        if self.state == 'PICK_GRIP':
            self.get_logger().info('📦 물건을 잡았습니다. 지정 좌표(-0.2, 0.0, 0.1)로 이동을 시작합니다.')
            self.state = 'PLACE_MOVE'
            self.send_pose_goal(-0.2, 0.0, 0.1)

        # [분기점 2] 물건 놓기(그리퍼 열기)가 끝난 상황이라면?
        elif self.state == 'PLACE_RELEASE':
            self.get_logger().info('🗑️ 물건을 놓았습니다. 복귀 좌표(0.1, 0.0, 0.2)로 이동을 시작합니다.')
            self.state = 'HOME_MOVE'
            self.send_pose_goal(0.1, 0.0, 0.2)

    def robot_tf_callback(self, msg):
        # 🎯 IDLE 상태일 때만 새로운 토픽 좌표를 받아들입니다.
        if self.state != 'IDLE':
            self.get_logger().warn(f'⏳ 로봇이 시퀀스 수행 중입니다 (현재 상태: {self.state}). 입력 무시.')
            return

        x, y, z = msg.x, msg.y, msg.z
        self.get_logger().info(f'📥 좌표 수신 완료 -> x: {x}, y: {y}, z: {z}')
        
        self.state = 'PICK_MOVE'
        self.send_pose_goal(x, y, z)

    def send_pose_goal(self, x, y, z):
        if not self._action_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('❌ MoveGroup 서버를 찾을 수 없습니다!')
            self.state = 'IDLE'
            return

        goal_msg = MoveGroup.Goal()

        req = MotionPlanRequest()
        req.group_name = 'arm'  
        req.allowed_planning_time = 5.0
        req.max_velocity_scaling_factor = 0.5
        req.max_acceleration_scaling_factor = 0.5

        target_pose = PoseStamped()
        target_pose.header.frame_id = 'world'
        target_pose.pose.position.x = float(x)
        target_pose.pose.position.y = float(y)
        target_pose.pose.position.z = float(z)
        target_pose.pose.orientation.w = 1.0  

        position_constraint = PositionConstraint()
        position_constraint.header.frame_id = 'world'
        position_constraint.link_name = 'end_effector_link'  
        
        bv = BoundingVolume()
        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.SPHERE
        primitive.dimensions = [0.01]  
        bv.primitives.append(primitive)
        bv.primitive_poses.append(target_pose.pose)
        
        position_constraint.constraint_region = bv
        position_constraint.weight = 1.0

        goal_constraints = Constraints()
        goal_constraints.position_constraints.append(position_constraint)
        req.goal_constraints.append(goal_constraints)
        
        goal_msg.request = req
        goal_msg.planning_options.plan_only = False

        self.get_logger().info(f'🚀 [{self.state}] 목표 좌표 향해 모터 기동 요청 전송!')
        self._send_goal_future = self._action_client.send_goal_async(goal_msg)
        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('❌ 목표 거부: 플래닝 실패.')
            self.state = 'IDLE'
            return

        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        """ 🎯 로봇 팔의 이동이 완전히 끝났을 때 불리는 콜백 함수 """
        result = future.result().result
        error_code = result.error_code.val
        
        if error_code == 1: # MoveItErrorCodes.SUCCESS == 1
            self.get_logger().info(f'🎉 [{self.state}] 목적지 도달 성공!')
            
            # [결과 분기 1] 첫 카메라 좌표에 도착했다면 ➔ 그리퍼 닫기 실행
            if self.state == 'PICK_MOVE':
                self.state = 'PICK_GRIP'
                self.send_gripper_goal(-0.009) # 닫기

            # [결과 분기 2] 지정한 이송 좌표(-0.2, 0.0, 0.1)에 도착했다면 ➔ 그리퍼 열기 실행
            elif self.state == 'PLACE_MOVE':
                self.state = 'PLACE_RELEASE'
                self.send_gripper_goal(0.019) # 열기 (1.9cm)

            # [결과 분기 3] 최종 복귀 좌표(0.1, 0.0, 0.2)에 도착했다면 ➔ 시퀀스 종료 및 IDLE 전환
            elif self.state == 'HOME_MOVE':
                self.get_logger().info('✨ 모든 픽앤플레이스 시퀀스가 성공적으로 끝났습니다! 새 토픽을 대기합니다.')
                self.state = 'IDLE' # 👈 다시 IDLE이 되어야 새로운 /robot_tf 토픽을 처리할 수 있습니다.

        else:
            self.get_logger().error(f'🤖 구동 실패. MoveIt 내부 에러 코드: {error_code}')
            self.state = 'IDLE' # 실패 시 대기 상태로 강제 전환


def main(args=None):
    rclpy.init(args=args)
    client = MoveItPoseClient()
    try:
        rclpy.spin(client)
    except KeyboardInterrupt:
        pass
    finally:
        client.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()