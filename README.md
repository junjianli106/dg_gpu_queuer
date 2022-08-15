# dg_gpu_queuer
![](https://img.shields.io/badge/License-GNU%20General%20Public%20License%20v3.0-green)
![](https://img.shields.io/badge/Python-3.8-blue)
![](https://img.shields.io/badge/Databse-Redis-blue)
![](https://img.shields.io/badge/知乎-一个邓-orange)

![](https://github.com/appleloveme/dg_gpu_queuer/blob/main/imgs/screenshot.png)

[博客](https://zhuanlan.zhihu.com/p/552967858)

一行代码实现GPU自动选择、GPU任务排队！即插即用！

一条命令实现Redis数据维护、GPU信息统计！随时随地查看GPU占用情况！

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
 
## 随时随地随用

手机端和电脑端均可通过Redis客户端来实时查看自己的任务排队情况、GPU占用情况等各种信息，并可调整任务队列！

## Redis客户端推荐

ios： [RediFri](https://apps.apple.com/cn/app/redifri/id1448152677?l=de)   免费

mac： [AnotherRedisDesktopManager](https://github.com/qishibo/AnotherRedisDesktopManager)    免费

![](https://github.com/appleloveme/dg_gpu_queuer/blob/main/imgs/mac.png)

