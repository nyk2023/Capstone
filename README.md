# Capstone

# 1. 필요한 것

## (1) 하드웨어

- 서버 (그래픽 카드 4090)
- Open Manipulator X vs SO101
- 컨베이어 벨트
- realsense D435i

## (2) 소프트웨어

- Ubuntu 22.04
- 그래픽 드라이버 570
- isaac sim 5.0.0
- cuda 12.4, cudnn 11.8
- isaac lab
- VS code / anaconda
- yolo vs patchcore

# 2. 참고 자료

## (1) pick&place 로직 제어

open manipulator x 키보드 구동 및 pick & place 로직 파이썬 코드 참고 가능

https://cobang.tistory.com/113

## (2) VLA

KIRIA(한국로봇산업진흥원) 교육 자료로 개발 환경 구축부터 Open VLA, LIBERO 사용 튜토리얼까지 실습 해볼 수 있음

## (3) Isaac Sim & Isaac Lab

NVIDIA에서 제공하는 Isaac Sim & Isaac Lab documentation 자료를 통해 시뮬레이션 환경 구축 및 로봇 모방학습 제어에 관한 자료 참고 가능

https://isaac-sim.github.io/IsaacLab/main/index.html

https://docs.isaacsim.omniverse.nvidia.com/latest/index.html

## (4) lerobot

SO101 제작 회사에서 Hugging Face를 통해 제공하는 documentation에서 VLA, Imitation Learning 등 참고 가능

https://huggingface.co/docs/lerobot/so101

# 3. 관련된 선행 연구 (우리의 차별점)

## (1) pick and place

- Open Manipulator X를 이용한 Pick and Place
    
    https://www.youtube.com/shorts/j1cOe4H7DIc?feature=share
    
- SO 101을 이용한 Pick and Place
    
    https://youtu.be/EE0oKUjc67Q?si=lcdY2pgskwG1zYP5
    
- Isaac Sim을 이용해 시뮬레이션 한 Pick and Place
    
    https://youtu.be/NvKx7VGrlgk?si=MvxxZUw32zQyqpIL
    

## (2) Dynamic pick and place

- 흡착 방식의 pick and place
    
    https://youtube.com/shorts/4z5QxKwHLOc?si=P66zCO9agLTCPyvH
    
- 정적 Pick and place
    
    https://www.youtube.com/shorts/RDjJOJ2_K74?feature=share
    

## (3) VLM

- 작업 내용을 이야기할 수 있는 VLM
    
    https://www.youtube.com/watch?v=wGNQ5-glDoU
    

# 4. 계획

1. 아이작심 환경 구축 
2. 참고자료 튜토리얼 한번씩 해보기
3. 움직이는 물체 먼저 잡는 기술 구현
4. 비전 알고리즘 확장

# 20260429
1. 필요한 것
   Jetson, Open Manipulator X, RGB-D Camera*2, Server, 컨베이어 벨트
2. 회의 내용
   메인 기술 : 동적 Pick & Place
   Pick & Place의 경우 모방 학습 or Inverse Kinemastic
   IK의 경우 정확도가 높지 않을까 생각.
   아이작심 기반의 모방 학습의 경우 토크 값 변환 필요. (Isaac Sim은 0.0이 Default, 실제 OMX는 2200)

# 5. 진행 상황

1. 환경 구축
   Jetson에 JetPack 설치 완료.
   서버의 경우, 현재 연결 가능한 네트워크가 존재하지 않기에 구축 불가한 상황.
