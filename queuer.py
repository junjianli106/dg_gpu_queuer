import json
from nvitop import select_devices
import time
import os
import datetime
from redis import Redis

def set_config_gpus(config):
    redis_client = RedisClient()
    if config.use_gpu and isinstance(config.visible_cuda, str) and 'auto_select_' in config.visible_cuda:
        # 如果是自动选择GPU
        min_count = int(config.visible_cuda.split('auto_select_')[-1])
        gpus = select_devices(format='index', min_count=min_count,
                              min_free_memory=config.cuda_min_free_memory,
                              max_memory_utilization=config.cuda_max_memory_utilization)
        self_occupied_gpus = redis_client.get_self_occupied_gpus()
        available_gpus = list(set(gpus) - self_occupied_gpus)
        if len(available_gpus) > 0 and len(available_gpus) >= min_count:
            # 有足够可用GPU
            config.wait_gpus = False
            config.visible_cuda = available_gpus[:min_count]
            if isinstance(available_gpus, int):
                config.default_device = f'cuda:{available_gpus}'
            else:
                config.default_device = f'cuda:{available_gpus[0]}'
            redis_client.register_gpus(config)
            print(f"自动选择GPU：{str(config.visible_cuda)}")
        else:
            # 可用GPU不足
            if config.wait_gpus:
                # 排队
                config.task_id = redis_client.join_wait_queue(config)
            else:
                # 不排队
                raise Exception("可用GPU数量不足，建议使用排队功能！")
    elif config.use_gpu:
        # 如果指定了GPU
        reserve_gpus = config.visible_cuda
        min_count = len(reserve_gpus)
        self_occupied_gpus = redis_client.get_self_occupied_gpus()
        gpu_all_free = True
        for gpu in reserve_gpus:
            if gpu in self_occupied_gpus:
                gpu_all_free = False
        if not config.wait_gpus and not gpu_all_free:
            raise Exception("指定GPU并未全部空闲，建议使用排队功能！")
        elif gpu_all_free:
            available_gpus = reserve_gpus
            config.wait_gpus = False
            config.visible_cuda = available_gpus[:min_count]
            if isinstance(available_gpus, int):
                config.default_device = f'cuda:{available_gpus}'
            else:
                config.default_device = f'cuda:{available_gpus[0]}'
            redis_client.register_gpus(config)
        else:
            # 排队
            config.task_id = redis_client.join_wait_queue(config)
    else:
        # 使用CPU
        config.default_device = f'cpu'
        config.wait_gpus = False
        config.visible_cuda = []

    ###############################################
    # 检查是否需要等待Gpu
    ###############################################
    while config.use_gpu and config.wait_gpus:
        # 判断当前是否轮到自己
        if redis_client.is_my_turn(config):
            # 循环获取当前可用Gpu
            try:
                min_count = int(config.visible_cuda.split('auto_select_')[-1]) if isinstance(config.visible_cuda, str) and "auto_select_" in config.visible_cuda else len(config.visible_cuda)
                gpus = select_devices(format='index', min_count=min_count,
                                      min_free_memory=config.cuda_min_free_memory,max_memory_utilization=config.cuda_max_memory_utilization)
                self_occupied_gpus = redis_client.get_self_occupied_gpus()
                if not isinstance(config.visible_cuda, str):
                    # 如果指定了GPU
                    reserve_gpus = config.visible_cuda
                    gpu_all_free = True
                    for gpu in reserve_gpus:
                        if gpu in self_occupied_gpus:
                            gpu_all_free = False
                    if gpu_all_free:
                        available_gpus = reserve_gpus
                    else:
                        available_gpus = []
                    min_count = len(reserve_gpus)
                else:
                    # 自动选择
                    available_gpus = list(set(gpus) - self_occupied_gpus)

                if len(available_gpus) > 0 and len(available_gpus) >= min_count:
                    # 自动选择，确认等待
                    if config.confirm_gpu_free and config.last_confirm_gpus == available_gpus[:min_count]:
                        # 如果满足条件退出循环
                        print("发现足够可用GPU并二次确认成功！")
                        config.wait_gpus = False
                        config.visible_cuda = available_gpus[:min_count]
                        if isinstance(available_gpus, int):
                            config.default_device = f'cuda:{available_gpus}'
                        else:
                            config.default_device = f'cuda:{available_gpus[0]}'
                        redis_client.pop_wait_queue(config)
                        redis_client.register_gpus(config)
                        break
                    else:
                        # 设置单次确认空闲
                        print("发现足够可用GPU！即将进行二次确认！")
                        config.confirm_gpu_free = True
                        config.last_confirm_gpus = available_gpus[:min_count]
                        redis_client.update_queue(config)
                        time.sleep(30)
                        continue
                # 重置确认信息
                print("当前无足够可用GPU，继续等待......")
                if config.confirm_gpu_free:
                    print("二次确认失败，继续等待......")
                config.confirm_gpu_free = False
                config.last_confirm_gpus = []
                redis_client.update_queue(config)
                time.sleep(30)
            except Exception as e:
                print(e)
        else:
            # 排队ing......
            wait_num = len(redis_client.client.lrange('wait_queue', 0, -1)) - 1
            print(f"正在排队中！ 前方还有 {wait_num} 个训练任务！")
            time.sleep(60)

    return config


class RedisClient:
    def __init__(self):
        self.client = Redis(host='127.0.0.1',
                              port=6379,
                              decode_responses=True,
                              charset='UTF-8',
                              encoding='UTF-8')

    def get_self_occupied_gpus(self, only_gpus=True):
        """
        获取自己已经占用的Gpu序号
        """
        self_occupied_gpus = self.client.hgetall('self_occupied_gpus')
        if only_gpus:
            all_gpus = []
            for task in self_occupied_gpus.values():
                gpus = [int(device) for device in json.loads(task)["use_gpus"].split(",")]
                all_gpus.extend(gpus)
            return set(all_gpus)
        return [json.loads(g) for g in self_occupied_gpus.values()]

    def join_wait_queue(self, config):
        """
        加入等待队列
        """
        curr_time = datetime.datetime.now()
        creat_time = datetime.datetime.strftime(curr_time, '%Y-%m-%d %H:%M:%S')
        task_id = str(os.getpid()) + '*' + str(int(time.mktime(time.strptime(creat_time, "%Y-%m-%d %H:%M:%S"))))
        content = {
            "create_time": creat_time,
            "update_time": creat_time,
            "system_pid": os.getpid(),
            "task_id": task_id,
        }
        wait_num = len(self.client.lrange('wait_queue', 0, -1))
        self.client.rpush("wait_queue", json.dumps(content))
        if wait_num == 0:
            print(f"正在排队中！ 目前排第一位哦！")
        else:
            print(f"正在排队中！ 前方还有 {wait_num} 个训练任务！")
        print(f"tips: 如果想要对任务进行调整可以移步Redis客户端进行数据修改，只建议进行修改 want_gpus 参数以及删除训练任务操作，其他操作可能会影响Redis读取的稳定性")
        return task_id

    def is_my_turn(self, config):
        """
        排队这么长时间，是否轮到我了？
        """
        curr_task = json.loads(self.client.lrange('wait_queue', 0, -1)[0])
        return curr_task['task_id'] == config.task_id

    def update_queue(self, config):
        """
        更新等待队列
        """
        task = json.loads(self.client.lrange('wait_queue', 0, -1)[0])
        if task['task_id'] != config.task_id:
            # 登记异常信息
            print("当前训练任务并不排在队列第一位，请检查Redis数据正确性！")
        curr_time = datetime.datetime.now()
        update_time = datetime.datetime.strftime(curr_time, '%Y-%m-%d %H:%M:%S')
        task['update_time'] = update_time
        self.client.lset("wait_queue", 0, json.dumps(task))
        print("更新训练任务时间戳成功！")

    def pop_wait_queue(self, config):
        """
        弹出当前排位第一的训练任务
        """
        task = json.loads(self.client.lrange('wait_queue', 0, -1)[0])
        if task['task_id'] != config.task_id:
            # 登记异常信息
            print("当前训练任务并不排在队列第一位，请检查Redis数据正确性！")
        next_task = self.client.lpop("wait_queue")
        return next_task

    def register_gpus(self, config):
        """
        将当前训练任务登记到GPU占用信息中
        """
        curr_time = datetime.datetime.now()
        creat_time = datetime.datetime.strftime(curr_time, '%Y-%m-%d %H:%M:%S')
        if not config.task_id:
            task_id = str(os.getpid()) + '*' + str(int(time.mktime(time.strptime(creat_time, "%Y-%m-%d %H:%M:%S"))))
        else:
            task_id = config.task_id
        content = {
            "use_gpus": ','.join([str(gpu) for gpu in list(config.visible_cuda)]),
            "register_time": datetime.datetime.strftime(curr_time,
                                                        '%Y-%m-%d %H:%M:%S'),
            "system_pid": os.getpid(),
            "task_id": task_id,
        }
        self.client.hset("self_occupied_gpus", task_id, json.dumps(content))
        print("成功登记Gpu使用信息到Redis服务器！")

    def deregister_gpus(self, config):
        """
        删除当前训练任务的占用信息
        """
        task = self.client.hget("self_occupied_gpus", config.task_id)
        if task:
            self.client.hdel("self_occupied_gpus", config.task_id)
            print("成功删除Redis服务器上的Gpu使用信息！")
        else:
            print("无法找到当前训练任务在Redis服务器上的Gpu使用信息！或许可以考虑检查一下Redis的数据 🤔")

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

