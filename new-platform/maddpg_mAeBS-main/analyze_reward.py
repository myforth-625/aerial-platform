"""
分析训练奖励曲线
"""
import numpy as np
import matplotlib.pyplot as plt

# 加载奖励数据
rewards = np.load('rewards.npy')

print("=" * 60)
print("训练奖励数据分析")
print("=" * 60)
print(f"Episode数量: {len(rewards)}")
print(f"最小值: {rewards.min():.2f}")
print(f"最大值: {rewards.max():.2f}")
print(f"平均值: {rewards.mean():.2f}")
print(f"标准差: {rewards.std():.2f}")
print(f"\n前10个episode: {rewards[:10]}")
print(f"后10个episode: {rewards[-10:]}")
print(f"\n前10个episode平均值: {rewards[:10].mean():.2f}")
print(f"后10个episode平均值: {rewards[-10:].mean():.2f}")
print(f"增长幅度: {(rewards[-10:].mean() - rewards[:10].mean()) / rewards[:10].mean() * 100:.2f}%")

# 检查趋势
print("\n" + "=" * 60)
print("趋势分析")
print("=" * 60)

# 计算每50个episode的平均值
for i in range(0, len(rewards), 50):
    end = min(i + 50, len(rewards))
    avg = rewards[i:end].mean()
    print(f"Episode {i}-{end-1}: 平均奖励 = {avg:.2f}")

# 检查是否有异常值
print("\n" + "=" * 60)
print("异常值检查")
print("=" * 60)
q1 = np.percentile(rewards, 25)
q3 = np.percentile(rewards, 75)
iqr = q3 - q1
lower_bound = q1 - 1.5 * iqr
upper_bound = q3 + 1.5 * iqr
outliers = rewards[(rewards < lower_bound) | (rewards > upper_bound)]
print(f"Q1: {q1:.2f}, Q3: {q3:.2f}, IQR: {iqr:.2f}")
print(f"异常值数量: {len(outliers)}")
if len(outliers) > 0:
    print(f"异常值: {outliers}")

# 重新绘制图像（带更多信息）
plt.figure(figsize=(12, 6))
plt.plot(np.arange(len(rewards)), rewards, 'r-', linewidth=1.5, label='Episode Reward')
plt.axhline(y=rewards.mean(), color='b', linestyle='--', linewidth=1, label=f'Mean: {rewards.mean():.2f}')
plt.xlabel('Episode', fontsize=12)
plt.ylabel('Average Reward per Step', fontsize=12)
plt.title('Training Reward Curve', fontsize=14)
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('reward_analysis.png', dpi=150)
print("\n已保存分析图像: reward_analysis.png")
plt.close()

print("\n" + "=" * 60)
print("结论")
print("=" * 60)
if rewards[-10:].mean() > rewards[:10].mean():
    print("✅ 训练正常：奖励在增长")
else:
    print("⚠️  警告：奖励没有增长")

if rewards.std() < rewards.mean() * 0.3:
    print("✅ 训练稳定：奖励波动在合理范围内")
else:
    print("⚠️  警告：奖励波动较大")



