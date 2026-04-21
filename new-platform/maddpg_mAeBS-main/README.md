<a name="hor6O"></a>
# MADDPG
<a name="Cgm27"></a>
## 代码包文件
github: 

- /models -- 保存训练模型
- main.py -- 主程序；run main
- environment.py -- 环境
- model.py
- multiagents.py
- replay_buffer.py
- core.py
- user_location_3_100 -- 用户位置数组（高斯分布、3簇、100个用户）

​

注：

- 一般只需要修改main和env两个文件
- 用户位置是n个用户的坐标 [[x1,y1],[x2,y2],...,[xn,yn]]，可自己随机生成

---

<a name="1dae3241"></a>
### main.py
<a name="BkNwv"></a>
##### 0、超参数
```python
EPISODE = 400
STEP = 200
MEMORY_SIZE = 10000  # 默认为 1e6
BATCH_SIZE = 1256
GAMMA = 0.97
SOFT_UPDATE = 0.5  # tao = 1.0表示没用使用软更新，一般取的比较小，比如0.1或者0.01这样的值，可以提高学习的稳定性。
LR_A = 0.01  # actor 学习率
LR_C = 0.01  # critic 学习率
```
<a name="1c8cc152"></a>
##### 1、创建多智能体环境 env


```python
env = MultiAgentEnv()
```


<a name="f6307f2f"></a>
##### 2、创建智能体

<br />创建观察、动作空间<br />

```python
obs_shape_n = [env.observation_space[i].shape[0] for i in range(env.num_agents)]
action_shape_n = [env.action_space[i].n for i in range(env.num_agents)]
```

<br />创建各个智能体的actor、critic网络；创建经验回放池<br />

```
actors_cur, critics_cur, actors_tar, critics_tar, optimizers_a, optimizers_c = \
        get_trainers(env, env.num_agents, obs_shape_n, action_shape_n)
memory = ReplayBuffer(10000)
```

<br />调用get_trainers函数（神经网络建立）为各个智能体创建当前与目标actor-critics网络<br />

```
actors_cur = [None for _ in range(env.num_agents)]
critics_cur = [None for _ in range(env.num_agents)]
actors_tar = [None for _ in range(env.num_agents)]
critics_tar = [None for _ in range(env.num_agents)]
optimizers_c = [None for _ in range(env.num_agents)]
optimizers_a = [None for _ in range(env.num_agents)]
```

<br />注意建立critic网络的时候，使用的输入数据是全局的。MADDPG的设计是集中式训练，分布式执行，训练时是集中式地学习训练critic与actor。使用时actor只用知道局部信息就行。在训练的时候critic是需要其他智能体的策略信息。<br />

```
for i in range(env.num_agents):
    actors_cur[i] = openai_actor(obs_shape_n[i], action_shape_n[i]).to(device)
    critics_cur[i] = openai_critic(sum(obs_shape_n), sum(action_shape_n)).to(device)
    actors_tar[i] = openai_actor(obs_shape_n[i], action_shape_n[i]).to(device)
    critics_tar[i] = openai_critic(sum(obs_shape_n), sum(action_shape_n)).to(device)
    optimizers_a[i] = optim.Adam(actors_cur[i].parameters(), 1e-2)  # 学习率0.01
    optimizers_c[i] = optim.Adam(critics_cur[i].parameters(), 1e-2)
```

<br />目标网络更新使用软更新，在get_trainers中调用一次，保证刚开始的时候目标网络与当前网络一致，之后目标网络延迟更新<br />
<br />tao = 1.0表示没用使用软更新，一般取的比较小，比如0.1或者0.01这样的值，可以提高学习的稳定性。<br />

```
actors_tar = update_trainers(actors_cur, actors_tar, 1.0)           # update the target par using the cur
critics_tar = update_trainers(critics_cur, critics_tar, 1.0)
```
<a name="d8fe2cf5"></a>
###### 


<a name="c81f7b0e"></a>
##### 3、开始训练


<a name="environment.py"></a>
### environment.py
<a name="Q8iYq"></a>
##### 0、环境参数
与系统模型有关
<a name="pDgQr"></a>
##### 1、计算A2G路损
```python
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
                    self.height[i] / distance[i][j])  # theta[i][j] = math.asin(uav_height / d[i][j])
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
                if r[i][j]<pro_los[i][j]:
                    path_loss[i][j]=1 / pl_los[i][j]
                else:
                    path_loss[i][j] = 1 / pl_nlos[i][j]
                #path_loss[i][j] = 1 / (pl_los[i][j] * pro_los[i][j] + pl_nlos[i][j] * (1 - pro_los[i][j]))
        return path_loss
```
<a name="dcNq1"></a>
##### 2、APC聚类方案下的容量计算
```python
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
```
<a name="EG2Ho"></a>
##### 3、不聚类的对比方案下的容量计算
对比方案：_不聚类，用户与提供最强信号的一个mAeBS关联，考虑干扰_
```python
    def get_capability(self):
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
```
