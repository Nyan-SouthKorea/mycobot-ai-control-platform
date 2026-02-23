from mycobot_wrapper import MyCobotController
import time

ROBOT_IP_PATH = './IP_info.txt'
ROBOT_SPEED = 30

robot = MyCobotController(ROBOT_IP_PATH, default_speed=ROBOT_SPEED)

robot.connect()
robot.power_on()
robot.torque_on()

# robot.home()

robot.move_world([170, 0, 290, -91, 44, -90], 1)






    

