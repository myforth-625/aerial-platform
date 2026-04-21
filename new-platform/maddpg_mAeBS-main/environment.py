# 环境、主要是动作状态空间
# 1、关于collide,需要再研究
# 2、关于观测 observation
# 3、何处更新智体位置、全局locations (update)
# 4、添加噪声？
import gym
import math
import numpy as np
from gym import spaces
from gym.envs.registration import EnvSpec
from sklearn.cluster import AffinityPropagation
from core import Agent, User
from multiagents import MultiDiscrete


# environment for all agents in the multiagent world
# currently code assumes that no agents will be created/destroyed at runtime!

# time: 2021/04/02
class MultiAgentEnv(gym.Env):
    def __init__(self):
        """
        初始化系统模型
        """
        self.info_callback = None
        self.done_callback = None
        self.num_uavs = 5  # 无人机数量

        self.area_height = 6000  # 区域 6km × 6km
        self.area_width = 6000
        self.uav_height_min = 100  # 无人机飞行高度范围 [100,300]
        self.uav_height_max = 300

        self.frequency = 30000  # 载波频率（MHz）
        self.c = 300000  # 光速（km/s）
        self.env_a = 9.61  # 环境参数
        self.env_b = 0.16  # 环境参数
        self.yita_l = 1  # 环境参数
        self.yita_n = 20  # 环境参数
        self.bandwidth = 100  # 带宽（MHz）
        self.noise_power = 3.9810717055349565e-13  # 噪声功率（W）-174 dBm/Hz
        self.transmit_power = 100  # 空中基站发射功率（W）50dBm
        self.num_beams = 64  # 毫米波波束数
        self.gain_b = 0.9  # 毫米波旁瓣增益
        self.snr_db = []
        self.snr_threshold = 5
        self.tp_t = 2e-4  # Pilot duration ratio
        self.tau_t = self.tp_t
        self.theta_t = math.pi / 6  # 发射端波束宽度
        self.theta_r = math.pi / 6  # 接收端波束宽度
        self.gain_t = (2 - (2 - (1 - math.cos(self.theta_t))) * self.gain_b) / (1 - math.cos(self.theta_t))  # 发射端毫米波增益
        self.gain_r = (2 - (2 - (1 - math.cos(self.theta_r))) * self.gain_b) / (1 - math.cos(self.theta_r))  # 接收端毫米波增益

        self.dim_p = 3  # 物理二维平面---三维
        self.dim_c = 2  # 交流或不交流?其实没用到

        # 智能体即空中基站数量、位置
        self.num_agents = 4
        self.agents = [Agent() for i in range(self.num_agents)]
        for i, agent in enumerate(self.agents):
            agent.name = 'agent %d' % i
            # agent.height = 200                                          # 无人机高度
            agent.state.p_pos = np.array([2500, 2500, 200])  # 无人机初始位置坐标
            # agent.state.p_pos = np.random.randint(0, self.area_width, 2)   # 无人机初始位置坐标
            agent.collide = True  # 留给碰撞检测
            agent.silent = True  # 无人机初始不交流，没用到，一直是silent

        # 用户位置、数量
        self.num_users = 100

        self.reset()

        # 整个环境来看智能体、用户实体的位置信息，为计算reward
        self.locations = np.zeros((self.num_agents, 2))
        self.height = np.zeros((self.num_agents, 1))
        # self.user_locations = np.zeros((self.num_users, 2))
        # self.user_locations = np.zeros((self.num_users, 2))
        # self.user_locations = np.load("user_locations_3_100.npy")
        self.user_locations = self.generate_gaussian_users()  # Randomize on init

        for i, agent in enumerate(self.agents):
            self.locations[i], self.height[i] = self.state_to_location(agent.state.p_pos)
            # self.locations[i] = agent.state.p_pos
            # self.height[i] = agent.height
        # for i, user in enumerate(self.users):
        #    self.user_locations[i] = user.state.p_pos

        # 系统初始容量、用户与无人机初始关联
        self.path_loss = self.get_path_loss()
        self.uav_ue_set = self.get_uav_ue_set()
        self.capability = self.get_capability()
        print('init capability =', self.capability)
        # 离散动作空间
        self.discrete_action_space = True
        # if true, action is a number 0...N, otherwise action is a one-hot N-dimensional vector
        self.discrete_action_input = False
        # if true, every agent has the same reward
        self.shared_reward = True  # 协作的环境
        self.time = 0

        # 动作、状态观测空间
        self.action_space = []
        self.observation_space = []
        for agent in self.agents:
            total_action_space = []
            # physical action space, 物理位置动作空间
            if self.discrete_action_space:
                u_action_space = spaces.Discrete(self.dim_p * 2 + 1)
            else:
                u_action_space = spaces.Box(low=-agent.u_range, high=+agent.u_range, shape=(self.dim_p,),
                                            dtype=np.float32)
            if agent.movable:
                total_action_space.append(u_action_space)

            # communication action space, 通信动作
            if self.discrete_action_space:
                c_action_space = spaces.Discrete(self.dim_c)
            else:
                c_action_space = spaces.Box(low=0.0, high=1.0, shape=(self.dim_c,), dtype=np.float32)
            if not agent.silent:
                total_action_space.append(c_action_space)

            # total action space
            if len(total_action_space) > 1:  # 说明该无人机既有u_action也有c_action
                # all action spaces are discrete, so simplify to MultiDiscrete action space
                if all([isinstance(act_space, spaces.Discrete) for act_space in total_action_space]):
                    act_space = MultiDiscrete([[0, act_space.n - 1] for act_space in total_action_space])  # 多离散动作空间
                else:
                    act_space = spaces.Tuple(total_action_space)
                self.action_space.append(act_space)  # 动作空间
            else:  # 只看else即可
                self.action_space.append(total_action_space[0])

            # observation space
            obs_dim = len(self.observation(agent))
            self.observation_space.append(spaces.Box(low=-np.inf, high=+np.inf, shape=(obs_dim,), dtype=np.float32))
            agent.action.c = np.zeros(self.dim_c)

        # rendering
        self.shared_viewer = True
        if self.shared_viewer:
            self.viewers = [None]
        else:
            self.viewers = [None] * self.num_agents
        self._reset_render()

        # simulation time step
        self.dt = 0.1
        # physical damping
        self.damping = 0.25

    def state_to_location(self, state):
        h = []
        for i in range(2, len(state), 3):
            h.append(state[i])
        location2d = [i for i in state if i not in h]
        location2d = np.array(location2d)
        # print(location2d)
        # location2d = location2d.reshape((self.num_agents, 2))
        h = np.array(h)
        return location2d, h

    def step(self, action_n):  # 需再认真看看
        """

        :param action_n:
        :return:
        """

        obs_n = []  # step后的新观察状态
        reward_n = []  # step所得reward
        done_n = []  # 执行与否
        info_n = {'n': []}  # 信息info
        # set action for each agent
        for i, agent in enumerate(self.agents):
            self._set_action(action_n[i], agent, self.action_space[i])  # 此处执行动作
            # print('x change =', agent.action.u[0], 'y change =', agent.action.u[1])

        # 需要根据动作更新状态
        # for i, agent in enumerate(self.agents):
        #     print(agent.state.p_pos)
        # print('here=', self.agents[0].action.u.shape)
        self.update()
        # print("------------")
        # for i, agent in enumerate(self.agents):
        #     print(agent.state.p_pos)

        # record observation for each agent
        for agent in self.agents:
            obs_n.append(self._get_obs(agent))  # 开源代码为从具体方案中调方法，这里直接实现
            reward_n.append(self._get_reward(agent))
            done_n.append(self._get_done(agent))

            info_n['n'].append(self._get_info(agent))

        # all agents get total reward in cooperative case
        reward = np.mean(reward_n)  # sum--> mean
        # print('reward =', reward)
        # reward = np.sum(reward_n)
        if self.shared_reward:
            reward_n = [reward] * self.num_agents
        return obs_n, reward_n, done_n, info_n

    def observation(self, agent):
        """
        observation with optimized dimensionality
        """
        # Get agent's current position
        agent_pos = agent.state.p_pos[:2]  # (x, y) in model space
        
        # Find nearest N terminals to reduce dimensionality
        N = 10  # Keep only 10 nearest terminals
        entity_pos = []
        
        if len(self.user_locations) > 0:
            # Calculate distances to all terminals
            distances = []
            for user_pos in self.user_locations:
                dist = np.sqrt(np.sum(np.square(agent_pos - user_pos)))
                distances.append((dist, user_pos))
            
            # Sort by distance and take nearest N
            distances.sort(key=lambda x: x[0])
            nearest_terminals = [pos for _, pos in distances[:N]]
            
            # Pad with zeros if there are fewer than N terminals
            while len(nearest_terminals) < N:
                nearest_terminals.append(np.array([0.0, 0.0]))
            
            entity_pos = nearest_terminals
        else:
            # If no terminals, use N zeros
            entity_pos = [np.array([0.0, 0.0]) for _ in range(N)]
        
        # Normalize Agent State
        # x, y in [0, 6000] -> [0, 1]
        # z in [100, 300] -> divide by 300 approx [0.33, 1.0]
        norm_p_pos = np.array([
            agent.state.p_pos[0] / self.area_width,
            agent.state.p_pos[1] / self.area_height,
            agent.state.p_pos[2] / 300.0 
        ])

        # Normalize User Positions - unified normalization to training environment size
        norm_entity_pos = []
        for pos in entity_pos:
            norm_entity_pos.append(pos[0] / self.area_width)
            norm_entity_pos.append(pos[1] / self.area_height)
            
        norm_entity_pos_flat = np.array(norm_entity_pos)

        return np.concatenate([norm_p_pos, norm_entity_pos_flat])

    def reset(self):
        """
        reset world: set random initial states
        :return:
        """
        for agent in self.agents:
            agent.state.p_pos = np.array([2500, 2500, 200])
            # agent.state.p_pos = np.random.randint(0, self.area_width, 2)
            # agent.height = 100
            agent.u_noise = 0.15
        # for i, user in enumerate(self.users):
        #     user.state.p_pos = np.random.randint(0, self.area_width, 2)
        # reset renderer
        self._reset_render()
        # record observations for each agent

        self.locations = np.zeros((self.num_agents, 2))  # 这三项是否有必要成为环境属性
        self.height = np.zeros((self.num_agents, 1))
        # self.user_locations = np.load("user_locations_3_100.npy")
        self.user_locations = self.generate_gaussian_users() # Randomize on reset
        # self.user_locations = np.zeros((self.num_users, 2))
        for i, agent in enumerate(self.agents):
            self.locations[i], self.height[i] = self.state_to_location(agent.state.p_pos)
            # self.locations[i] = agent.state.p_pos
            # self.height[i] = agent.height
        # for i, user in enumerate(self.users):
        #    self.user_locations[i] = user.state.p_pos

        obs_n = []
        for agent in self.agents:
            obs_n.append(self._get_obs(agent))
        return obs_n

    def reset_test(self):
        # reset world
        # set random initial states
        for agent in self.agents:
            agent.state.p_pos = np.array([2500, 2500, 200])
            # agent.state.p_pos = np.random.randint(0, self.area_width, 2)
            # agent.height = 100
            agent.u_noise = 0
        # for i, user in enumerate(self.users):
        #     user.state.p_pos = np.random.randint(0, self.area_width, 2)
        # reset renderer
        self._reset_render()
        # record observations for each agent

        self.locations = np.zeros((self.num_agents, 2))  # 这三项是否有必要成为环境属性
        self.height = np.zeros((self.num_agents, 1))
        self.user_locations = np.load("user_locations.npy")
        # self.user_locations = np.zeros((self.num_users, 2))
        for i, agent in enumerate(self.agents):
            self.locations[i], self.height[i] = self.state_to_location(agent.state.p_pos)
            # self.locations[i] = agent.state.p_pos
            # self.height[i] = agent.height
        # for i, user in enumerate(self.users):
        #    self.user_locations[i] = user.state.p_pos

        obs_n = []
        for agent in self.agents:
            obs_n.append(self._get_obs(agent))
        return obs_n

    # reset rendering assets
    def _reset_render(self):
        self.render_geoms = None
        self.render_geoms_xform = None

    # set env action for a particular agent, 速度与移动的度量需调整以适应实际设计
    def _set_action(self, action, agent, action_space, time=None):
        agent.action.u = np.zeros(self.dim_p)
        agent.action.c = np.zeros(self.dim_c)
        # process action
        if isinstance(action_space, MultiDiscrete):
            act = []
            size = action_space.high - action_space.low + 1
            index = 0
            for s in size:
                act.append(action[index:(index + s)])
                index += s
            action = act
        else:
            action = [action]

        # 主要关心这部分
        if agent.movable:
            # physical action
            if self.discrete_action_input:
                agent.action.u = np.zeros(self.dim_p)  # (x,y)
                # process discrete action
                if action[0] == 1: agent.action.u[0] = -1.0  # left
                if action[0] == 2: agent.action.u[0] = +1.0  # right
                if action[0] == 3: agent.action.u[1] = -1.0  # down
                if action[0] == 4: agent.action.u[1] = +1.0  # up
            else:
                if self.discrete_action_space:  # 独热编码，悬停、右、左、上、下
                    agent.action.u[0] += action[0][1] - action[0][2]  # x
                    agent.action.u[1] += action[0][3] - action[0][4]  # y
                    agent.action.u[2] += action[0][5] - action[0][6]  # z
                else:
                    agent.action.u = action[0]
            sensitivity = 100.0  # 速度默认为5
            if agent.accel is not None:
                sensitivity = agent.accel
            agent.action.u *= sensitivity
            action = action[1:]  # 弹出action[0]

        if not agent.silent:
            # communication action
            if self.discrete_action_input:
                agent.action.c = np.zeros(self.dim_c)
                agent.action.c[action[0]] = 1.0
            else:
                agent.action.c = action[0]
            action = action[1:]
        # make sure we used all elements of action
        assert len(action) == 0

    # get observation for a particular agent
    def _get_obs(self, agent):
        return self.observation(agent)

    # get reward for a particular agent
    def _get_reward(self, agent):
        return self.reward(agent)

    # get done for a particular agent
    def _get_done(self, agent):
        if self.done_callback is None:
            return False
        # return self.done(agent)

    # get info used for benchmarking
    def _get_info(self, agent):
        if self.info_callback is None:
            return {}
        # return self.info(agent)

    def get_path_loss(self):
        # 计算distance
        xiang1 = np.zeros((self.num_agents, self.num_users))
        xiang2 = np.zeros((self.num_agents, self.num_users))
        xiang3 = np.zeros((self.num_agents, 1))
        distance = np.zeros((self.num_agents, self.num_users))
        for i in range(self.num_agents):
            for j in range(self.num_users):
                xiang1[i][j] = math.pow((self.locations[i][0] - self.user_locations[j][0]), 2)
                xiang2[i][j] = math.pow((self.locations[i][1] - self.user_locations[j][1]), 2)
                xiang3[i] = math.pow(self.height[i], 2)
                distance[i][j] = math.sqrt(xiang1[i][j] + xiang2[i][j] + xiang3[i])

        # 计算pro_los
        theta = np.zeros((self.num_agents, self.num_users))
        pro_los = np.zeros((self.num_agents, self.num_users))
        for i in range(self.num_agents):
            for j in range(self.num_users):
                theta[i][j] = math.asin(
                    self.height[i] / distance[i][j]) * 180 / math.pi  # theta[i][j] = math.asin(uav_height / d[i][j])
                pro_los[i][j] = 1 / (1 + self.env_a * math.exp(-self.env_b * (theta[i][j] - self.env_a)))

        # 计算path_loss
        free_space = np.zeros((self.num_agents, self.num_users))
        free_space_xiang = 20 * math.log10(self.frequency) + 32.44
        # free_space_xiang = 20 * math.log10(self.frequency) + 20 * math.log(4 * math.pi / self.c)
        pl_los = np.zeros((self.num_agents, self.num_users))
        pl_nlos = np.zeros((self.num_agents, self.num_users))
        path_loss = np.zeros((self.num_agents, self.num_users))
        r = np.random.rand(self.num_agents, self.num_users)
        for i in range(self.num_agents):
            for j in range(self.num_users):
                free_space[i][j] = 20 * math.log10(distance[i][j] / 1000) + free_space_xiang
                pl_los[i][j] = free_space[i][j] + self.yita_l
                pl_los[i][j] = math.pow(10, pl_los[i][j] / 10)
                pl_nlos[i][j] = free_space[i][j] + self.yita_n
                pl_nlos[i][j] = math.pow(10, pl_nlos[i][j] / 10)
                if r[i][j] < pro_los[i][j]:
                    path_loss[i][j] = 1 / pl_los[i][j]
                else:
                    path_loss[i][j] = 1 / pl_nlos[i][j]
                # path_loss[i][j] = 1 / (pl_los[i][j] * pro_los[i][j] + pl_nlos[i][j] * (1 - pro_los[i][j]))
        return path_loss

    def get_uav_ue_set(self):
        # 每个用户选择信道条件最好的UAV进行初始关联
        association = self.path_loss.argmax(axis=0)
        uav_ue_set = [[] for i in range(self.num_agents)]
        # print(uav_ue_set)
        # 每个UAV所初始关联的用户index
        for i in range(self.num_agents):
            for j in range(self.num_users):
                if association[j] == i:
                    uav_ue_set[i].append(j)
        return uav_ue_set

    def get_capability(self):
        """
        APC聚类形成mAeBS-UE cooperative association
        :return:
        """
        # 计算相似度
        similarity = np.zeros((self.num_agents, self.num_agents))
        # print(similarity)
        for m in range(self.num_agents):
            for l in range(self.num_agents):
                for i in range(len(self.uav_ue_set[m])):
                    # print(uav_ue_set[l][i])
                    similarity[l][m] += self.path_loss[l][self.uav_ue_set[m][i]]

        # AP聚类
        af = AffinityPropagation().fit(similarity)
        cluster_centers_indices = af.cluster_centers_indices_  # 聚类中心的位置
        labels = af.labels_  # 类标签
        n_clusters_ = len(cluster_centers_indices)  # 簇的数量
        cluster_center = np.zeros((n_clusters_, 2))
        cluster_members = 0
        clustered_uavs_index = [[] for i in range(n_clusters_)]  # 按簇分UAVs index
        # cluster_members=[]
        for i in range(n_clusters_):
            for j in range(self.num_agents):
                if labels[j] == labels[cluster_centers_indices[i]]:
                    clustered_uavs_index[i].append(j)

        # 一簇内的所有无人机关联用户
        clustered_ue_set = [[] for i in range(len(clustered_uavs_index))]
        for i in range(len(clustered_uavs_index)):
            for j in range(len(clustered_uavs_index[i])):
                for k in range(len(self.uav_ue_set[clustered_uavs_index[i][j]])):
                    clustered_ue_set[i].append(self.uav_ue_set[clustered_uavs_index[i][j]][k])
        # print(clustered_ue_set)
        ns = np.zeros(len(clustered_ue_set))
        for i in range(len(clustered_ue_set)):
            ns[i] = len(clustered_ue_set[i])
        yita = np.zeros(len(clustered_ue_set))
        for i in range(len(clustered_ue_set)):
            if ns[i] > self.num_beams:
                yita[i] = self.num_beams / ns[i]
            else:
                yita[i] = 1
        received_power = np.zeros(self.num_users)
        yita1 = np.zeros(self.num_users)
        for i in range(len(clustered_uavs_index)):
            for j in range(len(clustered_ue_set[i])):
                for k in range(len(clustered_uavs_index[i])):
                    received_power[clustered_ue_set[i][j]] += self.path_loss[clustered_uavs_index[i][k]][
                                                                  clustered_ue_set[i][j]] * self.transmit_power \
                                                              * self.gain_t * self.gain_r
                    yita1[clustered_ue_set[i][j]] = yita[i]

        capability = 0
        self.snr_db = []
        for i in range(self.num_users):
            SNR = received_power[i] / self.noise_power
            if SNR == 0:
                SNR = 0.1
            self.snr_db.append(10 * (math.log10(SNR)))
            capability = capability + yita1[i] * (1 - self.tau_t) * self.bandwidth * math.log(1 + SNR, 2)

        return capability

    def get_capability_nocomp(self):
        """
        不聚类，用户与提供最强信号的一个mAeBS关联，考虑干扰
        :return:
        """
        # print(self.path_loss)
        association = self.path_loss.argmax(axis=0)
        # print(association)
        p_useful = np.max(self.path_loss, axis=0)
        # print(p_useful)
        p_all = np.sum(self.path_loss, axis=0)
        p_interference = p_all - p_useful
        # print(p_interference)
        # 每个用户的sinr
        sinr = self.transmit_power * p_useful * self.gain_t * self.gain_r / (
                p_interference * self.gain_b * self.gain_b * self.transmit_power + self.noise_power)
        # 波束
        yita1 = np.zeros(self.num_agents)
        yita = np.zeros(len(association))
        ns = np.zeros(self.num_agents)
        for i in range(self.num_agents):
            for j in range(len(association)):
                if association[j] == i:
                    ns[i] += 1
        for i in range(len(ns)):
            if ns[i] > self.num_beams:
                yita1[i] = self.num_beams / ns[i]
            else:
                yita1[i] = 1
        for i in range(self.num_agents):
            for j in range(len(association)):
                if association[j] == i:
                    yita[j] = yita1[i]

        rate = np.zeros(self.num_users)
        for i in range(len(sinr)):
            rate[i] = yita[i] * (1 - self.tau_t) * self.bandwidth * math.log((1 + sinr[i]), 2)
        # print(rate)
        capability = np.sum(rate)

        return capability

    def reward(self, agent):
        # Agents are rewarded based on minimum agent distance to each landmark, penalized for collisions
        # rew = 0
        rew = self.capability
        
        # --- Repulsion / Collision Penalty ---
        # Penalize if too close to other agents to encourage dispersion
        safe_distance = 600.0 # meters minimum separation
        
        # Dynamic penalty factor based on current capability scale
        # Use 10% of current capability as the maximum penalty
        # This ensures penalty scales appropriately with system performance
        penalty_factor = max(1000.0, self.capability * 0.1) # Minimum penalty of 1000
        
        current_agent_idx = -1
        # Find index of current agent
        for i, a in enumerate(self.agents):
            if a is agent:
                current_agent_idx = i
                break
        
        if current_agent_idx != -1:
            for i, other in enumerate(self.agents):
                if i == current_agent_idx:
                    continue
                
                # Calculate distance between this agent and other agent
                # state.p_pos is [x, y, z]
                dist = np.sqrt(np.sum(np.square(agent.state.p_pos - other.state.p_pos)))
                
                if dist < safe_distance:
                    # Penalty increases as distance decreases
                    # e.g., if dist is 0, penalty is max. if dist is safe_distance, penalty is 0.
                    # Use a simple linear or step penalty
                    rew -= penalty_factor * (1 - dist/safe_distance) 
                    # print(f"Agent {current_agent_idx} too close to Agent {i} (dist={dist:.1f}), penalizing!")

        # for l in self.users:
        #     dists = [np.sqrt(np.sum(np.square(a.state.p_pos - l.state.p_pos))) for a in self.agents]
        #     rew -= min(dists)
        # 碰撞检测
        # if agent.collide:
        #     for a in self.agents:
        #         if self.is_collision(a, agent):
        #             rew -= 1
        return rew

    # 具体是啥玩意儿
    @property
    def entities(self):
        return self.agents + self.users

    # 根据动作更新状态,暂时不考虑用户、环境的变化
    def update(self):
        p_force = [None] * len(self.agents)
        sensitivity = 100.0
        for i, agent in enumerate(self.agents):
            if agent.movable:
                noise = np.random.randn(*agent.action.u.shape) * agent.u_noise if agent.u_noise else 0.0
                noise *= sensitivity
                # if agent.action.u[0] < 0:
                #     agent.state.p_pos[0] = max(agent.state.p_pos[0] + agent.action.u[0] + noise[0], 0)
                # else:
                #     agent.state.p_pos[0] = min(agent.state.p_pos[0] + agent.action.u[0] + noise[0], self.area_width)
                #
                # if agent.action.u[1] < 0:
                #     agent.state.p_pos[1] = max(agent.state.p_pos[1] + agent.action.u[1] + noise[1], 0)
                # else:
                #     agent.state.p_pos[1] = min(agent.state.p_pos[1] + agent.action.u[1] + noise[1], self.area_width)

                old_pos = agent.state.p_pos
                agent.state.p_pos = agent.state.p_pos + agent.action.u + noise
                if agent.state.p_pos[0] < 0 or agent.state.p_pos[0] >= self.area_width:
                    agent.state.p_pos = old_pos
                if agent.state.p_pos[1] < 0 or agent.state.p_pos[1] >= self.area_width:
                    agent.state.p_pos = old_pos
                if agent.state.p_pos[2] < self.uav_height_min or agent.state.p_pos[2] >= self.uav_height_max:
                    agent.state.p_pos = old_pos

        for agent in self.agents:
            # set communication state (directly for now)
            if agent.silent:
                agent.state.c = np.zeros(self.dim_c)
            else:
                noise = np.random.randn(*agent.action.c.shape) * agent.c_noise if agent.c_noise else 0.0
                agent.state.c = agent.action.c + noise
        # # gather forces applied to entities
        # p_force = [None] * len(self.entities)
        # # apply agent physical controls
        # p_force = self.apply_action_force(p_force)
        # # apply environment forces 环境噪声省略
        # # p_force = self.apply_environment_force(p_force)
        # # integrate physical state, 整合物理状态
        # self.integrate_state(p_force)
        # # update agent state
        # for agent in self.agents:
        #     self.update_agent_state(agent)

        for i, agent in enumerate(self.agents):
            self.locations[i], self.height[i] = self.state_to_location(agent.state.p_pos)
            # self.locations[i] = agent.state.p_pos
            # self.height[i] = agent.height
        # for i, user in enumerate(self.users):
        #    self.user_locations[i] = user.state.p_pos
        # print('new locations =', self.locations)
        self.path_loss = self.get_path_loss()
        self.uav_ue_set = self.get_uav_ue_set()
        self.capability = self.get_capability()
        # print('new capability =', self.capability)

    def generate_gaussian_users(self):
        num_clusters = np.random.randint(2, 5) # 2 to 4 clusters
        centers = np.random.rand(num_clusters, 2) * [self.area_width, self.area_height]
        std_dev = 600.0 # 600m spread

        users = []
        users_per_cluster = self.num_users // num_clusters
        
        for i in range(self.num_users):
            cluster_idx = i % num_clusters
            center = centers[cluster_idx]
            pos = center + np.random.randn(2) * std_dev
            users.append(pos)
            
        users = np.array(users)
        users[:, 0] = np.clip(users[:, 0], 0, self.area_width)
        users[:, 1] = np.clip(users[:, 1], 0, self.area_height)
        return users
