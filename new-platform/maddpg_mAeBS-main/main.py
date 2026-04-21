# Time: 2022-03-03
# File func: main func
# 程序入口、episode训练
# 1、环境、智体创建
# 2、get_trainers 创建神经网络
# 3、update_trainers 更新神经网络
# 4、agents_train 训练各智体的神经网络
import os
import time
import torch
import pickle
import argparse
import numpy as np
import os
import time
# os.environ['CUDA_VISIBLE_DEVICES'] = '2'
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt

from model import openai_actor, openai_critic
from replay_buffer import ReplayBuffer
# from multiagents import MultiAgents
from environment import MultiAgentEnv
# from environment_2 import MultiAgentEnv
import warnings
warnings.filterwarnings("ignore")
from warnings import simplefilter
simplefilter(action='ignore', category=FutureWarning)

print("DEBUG: Libraries imported.")

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

print("DEBUG: Starting main...")

# Hyper Parameters
EPISODE = 1000  # 1000个episode，每个200步
STEP = 200
MEMORY_SIZE = 10000  # 默认为 1e6
BATCH_SIZE = 1256
GAMMA = 0.97
SOFT_UPDATE = 0.1  # tao = 1.0表示没用使用软更新，一般取的比较小，比如0.1或者0.01这样的值，可以提高学习的稳定性。
LR_A = 0.01  # actor 学习率
LR_C = 0.01  # critic 学习率


# 为各个智能体创建当前与目标actor-critic网络
def get_trainers(env, num_agents, obs_shape_n, action_shape_n):
    """
    init the trainers or load the old model
    """
    actors_cur = [None for _ in range(env.num_agents)]
    critics_cur = [None for _ in range(env.num_agents)]
    actors_tar = [None for _ in range(env.num_agents)]
    critics_tar = [None for _ in range(env.num_agents)]
    optimizers_c = [None for _ in range(env.num_agents)]
    optimizers_a = [None for _ in range(env.num_agents)]
    input_size_global = sum(obs_shape_n) + sum(action_shape_n)

    for i in range(env.num_agents):
        actors_cur[i] = openai_actor(obs_shape_n[i], action_shape_n[i]).to(device)  # actor局部信息
        critics_cur[i] = openai_critic(sum(obs_shape_n), sum(action_shape_n)).to(device)  # critic全局信息
        actors_tar[i] = openai_actor(obs_shape_n[i], action_shape_n[i]).to(device)
        critics_tar[i] = openai_critic(sum(obs_shape_n), sum(action_shape_n)).to(device)
        optimizers_a[i] = optim.Adam(actors_cur[i].parameters(), LR_A)  # 学习率0.001
        optimizers_c[i] = optim.Adam(critics_cur[i].parameters(), LR_C)
    actors_tar = update_trainers(actors_cur, actors_tar, 1.0)  # update the target par using the cur
    critics_tar = update_trainers(critics_cur, critics_tar, 1.0)  # update the target par using the cur
    return actors_cur, critics_cur, actors_tar, critics_tar, optimizers_a, optimizers_c


# 更新神经网络
def update_trainers(agents_cur, agents_tar, tao):
    """
    update the trainers_tar par using the trainers_cur
    This way is not the same as copy_, but the result is the same
    out:
    |agents_tar: the agents with new par updated towards agents_current
    """
    for agent_c, agent_t in zip(agents_cur, agents_tar):
        key_list = list(agent_c.state_dict().keys())
        state_dict_t = agent_t.state_dict()
        state_dict_c = agent_c.state_dict()
        for key in key_list:
            state_dict_t[key] = state_dict_c[key] * tao + \
                                (1 - tao) * state_dict_t[key]
        agent_t.load_state_dict(state_dict_t)
    return agents_tar


# 训练神经网络
def agents_train(game_step, update_cnt, memory, obs_size, action_size, \
                 actors_cur, actors_tar, critics_cur, critics_tar, optimizers_a, optimizers_c):
    """
    use this func to make the "main" func clean
    par:
    |input: the data for training
    |output: the data for next update
    """
    # update all trainers, if not in display or benchmark mode
    # learning_start_step 50000
    if game_step > 1000 and \
            (game_step - 1000) % 20 == 0:
        if update_cnt == 0: print('\r=start training ...' + ' ' * 100)
        # update the target par using the cur
        update_cnt += 1

        # update every agent in different memory batch
        for agent_idx, (actor_c, actor_t, critic_c, critic_t, opt_a, opt_c) in \
                enumerate(zip(actors_cur, actors_tar, critics_cur, critics_tar, optimizers_a, optimizers_c)):
            if opt_c == None: continue  # jump to the next model update

            # sample the experience
            _obs_n_o, _action_n, _rew_n, _obs_n_n, _done_n = memory.sample( \
                BATCH_SIZE, agent_idx)  # Note_The func is not the same as others, batch size = 1256?

            # --use the date to update the CRITIC
            rew = torch.tensor(_rew_n, device=device, dtype=torch.float)  # set the rew to gpu
            done_n = torch.tensor(~_done_n, dtype=torch.float, device=device)  # set the rew to gpu
            action_cur_o = torch.from_numpy(_action_n).to(device, torch.float)
            obs_n_o = torch.from_numpy(_obs_n_o).to(device, torch.float)
            obs_n_n = torch.from_numpy(_obs_n_n).to(device, torch.float)
            action_tar = torch.cat([a_t(obs_n_n[:, obs_size[idx][0]:obs_size[idx][1]]).detach() \
                                    for idx, a_t in enumerate(actors_tar)], dim=1)
            q = critic_c(obs_n_o, action_cur_o).reshape(-1)  # q
            q_ = critic_t(obs_n_n, action_tar).reshape(-1)  # q_
            tar_value = q_ * GAMMA * done_n + rew  # q_*gamma*done + reward
            loss_c = torch.nn.MSELoss()(q, tar_value)  # bellman equation

            # 记录loss-critic
            loss_critic[agent_idx].append(loss_c)
            # print('loss_critic =', loss_c)
            l_c[agent_idx].append(loss_c.detach().cpu().numpy())

            opt_c.zero_grad()
            loss_c.backward()
            nn.utils.clip_grad_norm_(critic_c.parameters(), 0.5)
            opt_c.step()

            # --use the data to update the ACTOR
            # There is no need to cal other agent's action
            model_out, policy_c_new = actor_c( \
                obs_n_o[:, obs_size[agent_idx][0]:obs_size[agent_idx][1]], model_original_out=True)
            # update the aciton of this agent
            action_cur_o[:, action_size[agent_idx][0]:action_size[agent_idx][1]] = policy_c_new
            loss_pse = torch.mean(torch.pow(model_out, 2))

            loss_a = torch.mul(-1, torch.mean(critic_c(obs_n_o, action_cur_o)))

            # 记录loss—actor
            la = 1e-3 * loss_pse + loss_a
            loss_actor[agent_idx].append(la)
            l_a[agent_idx].append(la.detach().cpu().numpy())
            # print('loss_actor =', la)

            opt_a.zero_grad()
            (1e-3 * loss_pse + loss_a).backward()
            nn.utils.clip_grad_norm_(actor_c.parameters(), 0.5)
            opt_a.step()

        # save the model to the path_dir ---cnt by update number
        # if update_cnt > 0: #and update_cnt % 400 == 0:
        # time_now = time.strftime('%y%m_%d%H%M')
        # print('=time:{} step:{}        save'.format(time_now, game_step))
        # model_file_dir = os.path.join("models", '{}_{}_{}'.format( \
        # "simple_adversary", time_now, game_step))
        # if not os.path.exists(model_file_dir):  # make the path
        # os.mkdir(model_file_dir)
        # for agent_idx, (a_c, a_t, c_c, c_t) in \
        # enumerate(zip(actors_cur, actors_tar, critics_cur, critics_tar)):
        # torch.save(a_c, os.path.join(model_file_dir, 'a_c_{}.pt'.format(agent_idx)))
        # torch.save(a_t, os.path.join(model_file_dir, 'a_t_{}.pt'.format(agent_idx)))
        # torch.save(c_c, os.path.join(model_file_dir, 'c_c_{}.pt'.format(agent_idx)))
        # torch.save(c_t, os.path.join(model_file_dir, 'c_t_{}.pt'.format(agent_idx)))

        # update the tar par
        actors_tar = update_trainers(actors_cur, actors_tar, SOFT_UPDATE)
        critics_tar = update_trainers(critics_cur, critics_tar, SOFT_UPDATE)

    return update_cnt, actors_cur, actors_tar, critics_cur, critics_tar


if __name__ == '__main__':
    # init the env, agent and train the agents
    """step1: create the environment """
    print("DEBUG: Initializing Env...")
    env = MultiAgentEnv()
    t1 = time.time()
    """step2: create agents"""
    obs_shape_n = [env.observation_space[i].shape[0] for i in range(env.num_agents)]
    action_shape_n = [env.action_space[i].n for i in range(env.num_agents)]  # 各个智能体的观测空间、动作空间
    # 各个智体的actor-critic网络以及经验回放池
    actors_cur, critics_cur, actors_tar, critics_tar, optimizers_a, optimizers_c = \
        get_trainers(env, env.num_agents, obs_shape_n, action_shape_n)
    memory = ReplayBuffer(MEMORY_SIZE)  # 默认为 1e6

    print('=1 The {} agents are inited ...'.format(env.num_agents))
    print('=============================')

    # right now
    """step3: init the pars """
    obs_size = []
    action_size = []
    game_step = 0  # 从训练一开始计算，每个step都会自增，最大值为episode * step
    episode_cnt = 0  # episode计数
    update_cnt = 0  # 从开始learning计算 每隔fre更新计数
    t_start = time.time()

    loss_actor = [[] for _ in range(env.num_agents)]
    loss_critic = [[] for _ in range(env.num_agents)]
    l_a = [[] for _ in range(env.num_agents)]
    l_c = [[] for _ in range(env.num_agents)]

    means = []
    stds = []

    rew_n_old = [0.0 for _ in range(env.num_agents)]  # set the init reward
    agent_info = [[[]]]  # placeholder for benchmarking info
    episode_rewards = [0.0]  # sum of rewards for all agents
    agent_rewards = [[0.0] for _ in range(env.num_agents)]  # individual agent reward
    head_o, head_a, end_o, end_a = 0, 0, 0, 0
    for obs_shape, action_shape in zip(obs_shape_n, action_shape_n):
        end_o = end_o + obs_shape
        end_a = end_a + action_shape
        range_o = (head_o, end_o)
        range_a = (head_a, end_a)
        obs_size.append(range_o)
        action_size.append(range_a)
        head_o = end_o
        head_a = end_a

    print('=2 starting iterations ...')
    print('=============================')
    obs_n = env.reset()  # 开始训练,问题？应该放在循环里？
    avr_coverage_rate_0 = []

    for episode_gone in range(EPISODE):
        mean = []
        std = []
        # cal the reward print the debug data
        if game_step > 1 and game_step % 100 == 0:  # game_step即dqn中的learn_step_counter
            mean_agents_r = [round(np.mean(agent_rewards[idx][-200:-1]), 2) for idx in range(env.num_agents)]
            mean_ep_r = round(np.mean(episode_rewards[-200:-1]), 3)
            print('episode reward:{} agents mean reward:{}'.format(mean_ep_r, mean_agents_r))
        # 打印学习过程中的episode的奖励与每个智能体的平均奖励
        # print('are you ok?')
        print('=Training: steps:{} episode:{}'.format(game_step, episode_gone))

        for episode_cnt in range(STEP):  # 每个episode 200 step
            # get action with ε-greedy exploration
            reward_step = []
            action_n = []
            
            # ε-greedy exploration parameters
            epsilon_start = 1.0
            epsilon_end = 0.01
            epsilon_decay = 0.999
            epsilon = max(epsilon_end, epsilon_start * (epsilon_decay ** game_step))
            
            for agent, obs in zip(actors_cur, obs_n):
                if np.random.rand() < epsilon:
                    # Exploration: random action (1-7, where 1-6 are directions, 7 is no-op)
                    action = np.zeros(7)  # assuming 7 actions
                    action_idx = np.random.randint(0, 7)
                    action[action_idx] = 1.0
                    action_n.append(action)
                else:
                    # Exploitation: model's best action
                    action = agent(torch.from_numpy(obs).to(device, torch.float)).detach().cpu().numpy()
                    action_n.append(action)

            # interact with env
            new_obs_n, rew_n, done_n, info_n = env.step(action_n)

            # save the experience
            memory.add(obs_n, np.concatenate(action_n), rew_n, new_obs_n, done_n)
            # episode_rewards[-1] += np.sum(rew_n)
            episode_rewards[-1] += np.mean(rew_n)
            reward_step.append(np.mean(rew_n))
            for i, rew in enumerate(rew_n): agent_rewards[i][-1] += rew

            # train our agents
            update_cnt, actors_cur, actors_tar, critics_cur, critics_tar = agents_train( \
                game_step, update_cnt, memory, obs_size, action_size, \
                actors_cur, actors_tar, critics_cur, critics_tar, optimizers_a, optimizers_c)

            # update the obs_n
            game_step += 1
            obs_n = new_obs_n
            done = all(done_n)
            terminal = (episode_cnt >= 200 - 1)
            # print('episode_gone =', episode_gone, 'length =', len(episode_rewards))
            mean.append(np.mean(reward_step))
            std.append(np.std(reward_step))
            if done or terminal:
                episode_step = 0
                obs_n = env.reset()
                agent_info.append([[]])
                episode_rewards.append(0)
                for a_r in agent_rewards:
                    a_r.append(0)
                continue

        # if episode_gone > 300:

        #    count_0 = 0
        #    for i in range(len(env.snr_db)):
        #        if env.snr_db[i] < 10:
        #            count_0 = count_0 + 1
        #    coverage_rate_0 = 1 - (count_0 / env.num_users)
        #    avr_coverage_rate_0.append(coverage_rate_0)

        means.append(mean)
        stds.append(std)

    episode_rewards = [x / 200 for x in episode_rewards]
    episode_rewards.pop()
    r1 = episode_rewards[-100:]
    r1 = np.mean(r1)
    print("avr_r")
    print(r1)
    print("running time: " + str(time.time() - t1))
    # print("avr_coverage_rate_0")
    # print(np.mean(avr_coverage_rate_0))
    # print(np.max(avr_coverage_rate_0))

    np.save("rewards.npy", episode_rewards)
    plt.plot(np.arange(len(episode_rewards)), episode_rewards, 'r')  # 画收敛曲线 ######
    plt.savefig("reward.png")
    # plt.show()

    plt.close()

    for agent_idx in range(len(l_a)):
        np.save("loss_actor{}.npy".format(agent_idx), l_a[agent_idx])
        plt.plot(np.arange(len(l_a[agent_idx])), l_a[agent_idx])
        plt.legend(['uav_{}'.format(agent_idx)], loc='upper right')
    plt.ylabel('Loss_actor')
    plt.xlabel('training steps')
    plt.savefig("loss_actor.png")
    # plt.show()

    plt.close()
    for agent_idx in range(len(l_c)):
        np.save("loss_critic{}.npy".format(agent_idx), l_c[agent_idx])
        plt.plot(np.arange(len(l_c[agent_idx])), l_c[agent_idx])
        plt.legend(['uav_{}'.format(agent_idx)], loc='upper right')
    plt.ylabel('Loss_critic')
    plt.xlabel('training steps')
    plt.savefig("loss_critic.png")
    # plt.show()

    # save the model
    model_file_dir = os.path.join("models")
    if not os.path.exists(model_file_dir):
        # make the path
        os.mkdir(model_file_dir)
    for agent_idx, (a_c, a_t, c_c, c_t) in \
            enumerate(zip(actors_cur, actors_tar, critics_cur, critics_tar)):
        torch.save(a_c, os.path.join(model_file_dir, 'a_c_{}.pt'.format(agent_idx)))
        torch.save(a_t, os.path.join(model_file_dir, 'a_t_{}.pt'.format(agent_idx)))
        torch.save(c_c, os.path.join(model_file_dir, 'c_c_{}.pt'.format(agent_idx)))
        torch.save(c_t, os.path.join(model_file_dir, 'c_t_{}.pt'.format(agent_idx)))
    print("save the model")

    # print("locations")
    # print(env.locations)
    # print(env.height)
    # print("user_locations")
    # print(env.user_locations)

    # torch.save(actors_cur.cpu()[0].state_dict(), 'actors_cur_1.pth')
    # pretrained_net = torch.load('actors_cur_1.pth')
    # print(pretrained_net)
