from pymycobot import MyCobotSocket
import time

# ip 정보 읽어오기
with open('IP_info.txt', 'r', encoding='utf-8') as f:
    f = f.read()
    ip, port = f.split(', ')
    port = int(port)
    print(f'IP주소: {ip}, 포트: {port}')
mc = MyCobotSocket(ip, port)
mc.power_on()
time.sleep(1)



# 그리퍼 열기
speed = 100
mc.set_gripper_state(0, speed)   # 0 = open
time.sleep(1)

# 그리퍼 닫기
mc.set_gripper_state(1, speed)   # 1 = close
time.sleep(1)

# 그리퍼 열기
mc.set_gripper_state(0, speed)   # 0 = open
time.sleep(1)