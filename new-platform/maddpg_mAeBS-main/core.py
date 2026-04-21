# 动作、状态空间、智能体(无人机基站)、用户的基类
# 需要仔细看看删繁就简,用到的时候再改
import numpy as np

# physical/external base state of all entites
class EntityState(object):
    def __init__(self):
        # physical position, 位置
        self.p_pos = None
        # physical velocity, 速度
        self.p_vel = None

# state of agents (including communication and internal/mental state)
class AgentState(EntityState):
    def __init__(self):
        super(AgentState, self).__init__()
        # communication utterance, 是否交流说话
        self.c = None

# action of the agent
class Action(object):
    def __init__(self):
        # physical action, 物理动作
        self.u = None
        # communication action, 交流动作
        self.c = None

# 环境中实体的性质与状态
class Entity(object):
    def __init__(self):
        # 名称
        self.name = ''
        # 实体移动性
        self.movable = False
        # 实体与其他实体的碰撞性
        self.collide = True
        # 实体密度
        self.density = 25.0
        # color
        self.color = None
        # 速度与加速度
        self.max_speed = None
        self.accel = None
        # state
        self.state = EntityState()
        # 质量
        self.initial_mass = 1.0

    @property
    def mass(self):
        return self.initial_mass

# properties of user entities
class User(Entity):
     def __init__(self):
        super(User, self).__init__()
        # self.movable = True

# properties of agent entities
class Agent(Entity):
    def __init__(self):
        super(Agent, self).__init__()
        # agents are movable by default, 可移动
        self.location = None
        self.movable = True
        # cannot send communication signals, 可以交流
        self.silent = False
        # cannot observe the world, 可以观测
        self.blind = False
        # physical motor noise amount, 物理噪声
        self.u_noise = None
        # communication noise amount, 通信噪声
        self.c_noise = None
        # control range
        self.u_range = 1.0
        # state
        self.state = AgentState()
        # action
        self.action = Action()
        # script behavior to execute, 待执行的行为脚本
        self.action_callback = None

