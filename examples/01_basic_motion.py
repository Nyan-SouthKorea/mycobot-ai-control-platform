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



# -----------------------
# Joint 이동 1
# -----------------------
joint_1 = [0, 0, 0, 0, 0, 0]
mc.send_angles(joint_1, speed=40)


# -----------------------
# Joint 이동 2
# -----------------------
joint_2 = [20, -20, 30, 0, 40, 0]
mc.send_angles(joint_2, speed=40)


# -----------------------
# Linear 이동 1 (X 방향)
# -----------------------
p1 = mc.get_coords()
p2 = p1[:]
p2[0] += 40

mc.send_coords(p2, speed=20, mode=1)


# -----------------------
# Linear 이동 2 (Z 수직)
# -----------------------
p3 = mc.get_coords()
p4 = p3[:]
p4[2] -= 40

mc.send_coords(p4, speed=15, mode=1)


# -----------------------
# Joint 이동
# -----------------------
mc.send_angles([0.42, -14.06, -85.78, 100.81, -0.35, 43.41], speed=100)
