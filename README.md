# MOSEAC
The code is for RLC Finding the Frame paper: ''MOSEAC: Streamlined Variable Time Step Reinforcement Learning''.
<!--After our paper is available online, I'd add the related link here-->

## Model and Test Environment Architecture
We implement our variable control rate method based on the idea of [SEAC](https://github.com/alpaficia/SEAC_Pytorch_release)
algorithm . We called this method Multi-Objective Soft Elastic Actor and 
Critic (MOSEAC). It allows the agent to execute actions with elastic times for every time step, compared with SEAC, 
it has less hyperparameter dependence and better stability.

Traditional reinforcement learning (RL) methods typically employ a fixed control loop, where each cycle corresponds to 
an action. This rigidity poses challenges in practical applications, as the optimal control frequency is task-dependent.

The core of this algorithm is to follow the principle of reaction control and change the execution time of each action 
of the agent from the classical fixed value of almost all RLs to a more reasonable variable value within a suitable time
range. Moreover, This method features an adaptive reward scheme that adjusts hyperparameters based on observed trends in 
task rewards during training. This scheme reduces the complexity of hyperparameter tuning, requiring a single 
hyperparameter to guide exploration, thereby simplifying the learning process and lowering deployment costs. 

Our result has been verified within this Newton gymnasium environment.

Following these steps, you can reproduce the result in our paper.

## OS Environment
All commends in this page are based on the Ubuntu 22.04 OS. You may need to adjust some commands to fit other Linux, 
Windows, or macOS.
## Remote training with docker
We have already made a docker file for you. What you need to do is to launch it to build your docker image. You are 
welcome to change the path yourself. You can build the docker image by:
```
docker image build [OPTIONS] PATH_TO_DOCKERFILE
```
Then, you can launch it to the dockerhub or somewhere and transform it to your remote PC. And start training.

A [tutorial](https://docs.docker.com/get-started/) on how to use docker.

A [tutorial](https://developer.nvidia.com/nvidia-container-runtime) on how to use cuda with docker.

## Local training with your PC
If you want to train the model locally, and you don't want to speed up the training with local GPU(s), you need to 
install [PyTorch](https://pytorch.org/) first, then you can directly run:
```
cd PATH_TO_YOUR_FOLDER
RUN pip3 install -r requirement.txt
python3 main.py
```

If you want to speed up your training with GPU(s), you need to find out your 
[Nvidia Driver](https://www.nvidia.com/Download/index.aspx?lang=en-us) version and corresponding
[Cuda](https://developer.nvidia.com/cuda-downloads) and [CuDNN](https://developer.nvidia.com/rdp/cudnn-archive) 
versions, then install them first. Next, install the corresponding [PyTorch](https://pytorch.org/) version after all the Nvidia
and PyTorch environments are well setting. Finally, you can run:
```
cd PATH_TO_YOUR_FOLDER
RUN pip3 install -r requirement.txt
python3 main.py
```

For more parameter settings, please refer to the comments in the code.

We have tested our code on a PC with a Intel 13600K CPU and a NVIDIA RTX 4070 GPU, with the following software versions:

- Cuda: 11.8
- CuDNN: 8.9.5
- Driver: 550.67
- Pytorch: 2.0.1+cu118

The results are shown in the following images:

## Average Returns
Average returns for three algorithms trained in 1.2 million steps. The figure on the right is a partially enlarged 
version of the figure on the left.

<img src="img/average_reward.jpg" style="zoom:80%" />

## Training Speed (Average Energy Cost)
Average time cost per episode for three algorithms trained in 1.2 millions steps. The figure on the right is a partially
enlarged version of the figure on the left.

<img src="img/average_energy_cost.jpg" style="zoom:80%" />

##  Energy Performance Raincloud Graph:
Four example tasks show how SEAC changes the control rate dynamically to adapt to the Newtonian mechanics environment 
and ultimately reasonably complete the goal.

<img src="img/energy.jpg" style="zoom:76%" />

## Time Performance Raincloud Graph:
The energy cost for 100 trials. SEAC consistently reduces the number of time steps compared with PPO and SAC without 
affecting the overall average reward. Therefore, SAC and PPO are not optimizing for energy consumption and have a much 
larger spread.

<img src="img/time.jpg" style="zoom:100%" />

More explanation, implementation and parameters related details, please refer to our paper.
<!--After our paper is available online, I'd add the cite information here-->

## License
MIT

## Contact Information
Author: Dong Wang (dong-1.wang@polymtl.ca), Giovanni Beltrame (giovanni.beltrame@polymtl.ca)

And welcome to contact [MISTLAB](https://mistlab.ca) for more fun and practical robotics and AI related projects and 
collaborations. :)

![image7](img/mistlogo.svg)
