# 한경국립대 AI반도체융합전공 PAP

해당 package는 기존에 ROBOTIS에서 제공하는 Open Manipulator X를 구동하는 package에 Pick and Place하는 내용을 수정하였습니다.

- 참고 : https://emanual.robotis.com/docs/en/platform/openmanipulator_x/overview/ 




## 구동 방법
- 로봇 구동
```
ros2 launch open_manipulator_x_bringup hardware.launch.py
```
- moveit & rviz2 실행
```
ros2 launch open_manipulator_x_moveit_config moveit_core.launch.py
```
- Camera와 End_effector 거리 조정
```
ros2 run tf2_ros static_transform_publisher -0.065 0.0 0.08 -1.5708 0 -1.5708 end_effector_link camera_frame
```
- 객체 인식 및 Topic Publish
```
python3 colcon_ws/src/pick_and_place/robot_tf.py
```
- Inverse Kinematics를 기반으로한 Pick And Place 수행
```
ros2 run open_manipulator_x_moveit_config ik_test.py
```
