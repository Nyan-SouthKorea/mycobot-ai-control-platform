from pymycobot import MyCobotSocket
mc = MyCobotSocket("192.168.31.239", 9000)

# 현재 모터 값 출력
print(mc.is_controller_connected())  # 정상: 1
print(mc.get_angles())               # 정상: [6개 각도]

# 전체 기능 출력하고 시작
methods = []
for name in dir(mc):
    if name.startswith("_"):
        continue
    attr = getattr(mc, name)
    if callable(attr):
        methods.append(name)

print(f"method count = {len(methods)}")
print("\n".join(sorted(methods)))

mc.power_on()