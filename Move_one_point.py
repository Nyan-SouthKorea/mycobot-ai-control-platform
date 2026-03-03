from mycobot_wrapper import MyCobotController
import time

ROBOT_IP_PATH = './IP_info.txt'
ROBOT_SPEED = 50

robot = MyCobotController(ROBOT_IP_PATH, default_speed=ROBOT_SPEED)

robot.connect()
robot.power_on()
robot.torque_on()

# robot.home()

robot.move_joints([-51.9, 7.64, -100.45, 97.38, -30.05, -49.21], 1)
# robot.move_world([-51.9, 7.64, -100.45, 97.38, -30.05, -49.21], 1)



# robot.gripper_open_retry()
# robot.gripper_close_retry()






