# dg_gpu_queuer
![](https://img.shields.io/badge/License-GNU%20General%20Public%20License%20v3.0-green)
![](https://img.shields.io/badge/Python-3.8-blue)
![](https://img.shields.io/badge/Databse-Redis-blue)
![](https://img.shields.io/badge/知乎-一个邓-orange)

![](https://github.com/appleloveme/dg_gpu_queuer/blob/main/imgs/screenshot.png)

[博客](https://zhuanlan.zhihu.com/p/552967858)

超轻量级！

一行代码实现GPU自动选择、GPU任务排队！即插即用！

一条命令实现Redis数据维护、GPU信息统计！随时随地查看GPU占用情况！

支持等待指定GPU，支持自动选择！

## 数据库安装

Redis安装可参考 [一个邓：非Root用户在Linux安装Redis并允许远程连接此数据库](https://zhuanlan.zhihu.com/p/552627015)

## 依赖包

GPU监控工具引用自[nvitop](https://github.com/XuehaiPan/nvitop)

安装Python对Redis的依赖包[Redis](https://github.com/redis/redis-py)

    pip install nvitop
    pip install redis


## 运行GPU自动选择、GPU任务排队


    python queuer.py


推荐使用Hydra Config类作为配置类，Demo中为了方便演示以及兼容各种框架，使用了普通配置类

## 运行Redis数据维护、GPU信息统计

    nohup python maintain_redis_data.py
    
 定时（默认为3s）更新Redis信息，删除掉“死进程”对应的值，并将GPU的占用情况、进程信息上传到Redis并维护
 
 当想在自己的代码中使用时，只需使用
 
    config = set_config_gpus(config)
        
 调用环境上下文
 
    class Config:

        use_gpu = True
        wait_gpus = True  # 是否愿意接受排队等待
        cuda_max_memory_utilization = 0.2  # nvitop的gpu最大内存使用阈值
        cuda_min_free_memory = "35GiB"  # nvitop的gpu最大内存使用量
        visible_cuda = 'auto_select_1'  # 使用“auto_select_[想要使用的GPU数量]”前缀自动选择可用GPU，或者使用列表指定GPU
        # visible_cuda = [1, 2, 3, 6]  # 使用“auto_select_[想要使用的GPU数量]”前缀自动选择可用GPU，或者使用列表指定GPU

        # 以下为自动调整参数，无需手动改
        default_device = "cuda:0"  # 程序自动调整，默认的设备
        task_id = None  # 程序自动调整，如果选择等待GPU，那么这将是排队的号，此处无需填写，由程序自动生成
        confirm_gpu_free = False  # 程序自动调整，用于标识当前训练任务是否已经确认了GPU出于空闲，如果两次都等到了相同的GPU那么就认为该GPU空闲
        last_confirm_gpus = None  # 程序自动调整，记录第一次确认空闲的gpus

    if __name__ == '__main__':
        config = Config()
        config = set_config_gpus(config)
        print()

 即可获取到可用GPU，支持等待指定GPU，也支持自动选择
 
## 随时随地随用

手机端和电脑端均可通过Redis客户端来实时查看自己的任务排队情况、GPU占用情况等各种信息，并可调整任务队列！

## Redis客户端推荐

ios： [RediFri](https://apps.apple.com/cn/app/redifri/id1448152677?l=de)   免费

mac： [AnotherRedisDesktopManager](https://github.com/qishibo/AnotherRedisDesktopManager)    免费

![](https://github.com/appleloveme/dg_gpu_queuer/blob/main/imgs/mac.png)

注意：要想随时随地查看Redis信息，脱离内网使用，需要将内网网址替换为内网穿透的网址！

使用请注明出处！谢谢

