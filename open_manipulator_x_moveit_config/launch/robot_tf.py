#!/usr/bin/env python3

import time, json, os
import cv2
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped  
from geometry_msgs.msg import Point         
import tf2_ros
from tf2_geometry_msgs import do_transform_point

def load_model():
    model = YOLO("best.pt")
    return model

model = load_model()

rclpy.init()
node = Node('tf_publisher')

coords_pub = node.create_publisher(Point, 'robot_tf', 10)

tf_buffer = tf2_ros.Buffer()
tf_listener = tf2_ros.TransformListener(tf_buffer, node)

pipe = rs.pipeline()
selection = pipe.start()
depth_stream = selection.get_stream(rs.stream.depth).as_video_stream_profile()
resolution = (depth_stream.width(), depth_stream.height())
i = depth_stream.get_intrinsics()
principal_point = (i.ppx, i.ppy)
focal_length = (i.fx, i.fy)
cam_model = i.model

# rgb 카메라 기준으로 depth 카메라와 정렬하기 위한 align 객체 생성
align_to = rs.stream.color
align = rs.align(align_to)

save_path = "detected_info.json"

time.sleep(1)

start_time = time.time()
print("프로그램이 시작되었습니다. 20초 동안 카메라 스트리밍을 유지하며 대기합니다...")

try:
    while rclpy.ok():
        
        rclpy.spin_once(node, timeout_sec=0.001)
        
        frames = pipe.wait_for_frames()
        aligned_frames = align.process(frames)
        color_frame = aligned_frames.get_color_frame()
        depth_frame = aligned_frames.get_depth_frame()
        
        if not color_frame or not depth_frame:
            continue

        frame = np.asanyarray(color_frame.get_data())
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) # rgb를 bgr로 변환
        
        result = model(frame, conf=0.5, classes=[0], verbose=False)
        
        annotated_frame = frame.copy()
        info = {}
        
        # --- [수정] 현재 몇 초가 흘렀는지 계산 ---
        elapsed_time = time.time() - start_time
        
        for res in result:
            for box in res.boxes:
                cls = int(box.cls[0].item())
                xmin, ymin, xmax, ymax = map(int, box.xyxy[0])
                conf = round(box.conf[0].item(), 2)
                label = res.names.get(cls, str(cls))
                
                center_x = (xmin + xmax) // 2
                center_y = (ymin + ymax) // 2
                depth = depth_frame.get_distance(center_x, center_y)
                depth_mm = int(depth * 1000)
                
                point = rs.rs2_deproject_pixel_to_point(i, [center_x, center_y], depth)
                xc, yc, zc = point[0], point[1], point[2]
                rx, ry, rz = 0.0, 0.0, 0.0
                
                # 화면 표시용 딕셔너리 채우기
                obj = {
                    "bbox": [xmin, ymin, xmax, ymax],
                    "depth": depth_mm,
                    "camera_xyz": [xc, yc, zc],
                    "robot_xyz" : [rx, ry, rz],
                    "confidence": conf
                }
                info.setdefault(label, []).append(obj)
                
                cv2.rectangle(annotated_frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
                cv2.putText(
                    annotated_frame, f"{label} {conf} {depth_mm}mm", (xmin, ymin - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1
                )

        # --- [핵심 수정] 20초가 지난 시점이라면 딱 한 번 실행하고 프로그램 완전히 종료 ---
        if elapsed_time >= 10.0:
            print(f"\n[★ 20초 경과] 현재 프레임에서 인식된 객체 좌표를 전송합니다.")
            
            # 인식된 데이터가 있을 때만 처리
            if info:
                # 첫 번째 인식된 객체의 좌표를 가져와 TF 변환 진행 (기존 로직 보존)
                for label, objs in info.items():
                    for target_obj in objs:
                        xc, yc, zc = target_obj["camera_xyz"]
                        
                        camera = PointStamped()
                        camera.header.frame_id = 'camera_frame' 
                        camera.header.stamp = node.get_clock().now().to_msg()
                        camera.point.x = xc
                        camera.point.y = yc
                        camera.point.z = zc
                        
                        try:
                            transform = tf_buffer.lookup_transform(
                                'world', camera.header.frame_id, rclpy.time.Time(),
                                timeout=rclpy.duration.Duration(seconds=0.5) # 타임아웃을 0.5초로 늘려 안정성 확보
                            )
                        
                            robot = do_transform_point(camera, transform)
                            rx, ry, rz = robot.point.x, robot.point.y, robot.point.z
                            
                            # 객체 데이터에 로봇 좌표 갱신
                            target_obj["robot_xyz"] = [rx, ry, rz]
                            
                            # ROS 2 토픽 발행 (딱 한 번)
                            move_msg = Point()
                            move_msg.x = rx
                            move_msg.y = ry
                            move_msg.z = rz
                            coords_pub.publish(move_msg)
                            
                            print(f"-> 토픽 전송 완료! X: {rx:.4f}, Y: {ry:.4f}, Z: {rz:.4f}")
                        except Exception as e:
                            print(f"-> TF 변환 실패: {e}")
                
                # 딱 한 번만 JSON 파일 저장
                with open(save_path, "w", encoding="utf-8") as file:
                    json.dump(info, file, ensure_ascii=False, indent=2)
                print("-> 인식 결과 JSON 저장 완료.")
            else:
                print("-> 20초 시점에 화면에 인식된 대상(클래스 67)이 없습니다.")
                
            print("목표를 달성하여 프로그램을 종료합니다.")
            break # [★ 중요] while 루프를 완전히 탈출하여 종료 프로세스로 이동합니다.

        # 20초 전에는 터미널에 아무것도 찍지 않고 조용히 화면만 보여줍니다.
        cv2.imshow('test', annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
finally:
    # 루프를 탈출(break)하면 리소스들이 깔끔하게 닫힙니다.
    pipe.stop()
    cv2.destroyAllWindows()
    node.destroy_node()
    rclpy.shutdown()
    print("프로그램이 정상적으로 닫혔습니다.")
