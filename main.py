from InquirerPy import inquirer

from api import API
from utils import get_ntp_time

from loguru import logger

import time
import asyncio

async def main():
    logger.warning("本系统未在实际环境测试，不保证最终功能可靠性，请谨慎使用！")

    logger.info("开始登录")
    personsn = await inquirer.text(
        message="请输入学号",
        validate=lambda x: len(x) > 0 or "学号不能为空"
    ).execute_async()

    password = await inquirer.text(
        message="请输入密码",
        validate=lambda x: len(x) > 0 or "密码不能为空"
    ).execute_async()

    logger.warning("目前学号密码认证非常逆天，不验证验证码正确性，请等待提示出现再输入验证码")

    api_client = API(personsn=personsn, password=password)
    
    login_flag = False
    while not login_flag:
        try:
            await api_client._get_vertification_code()
            input_code = await inquirer.text(
                message="请输入验证码",
                validate=lambda x: len(x) > 0 or "验证码不能为空"
            ).execute_async()
            login_flag = await api_client.login(input_code)
            logger.debug(f"登录状态: {login_flag}")
            logger.info("登录成功")
        except Exception as e:
            logger.error(f"登录失败: {e}")
            retry = await inquirer.confirm(
                message="登录失败，是否重试？",
                default=True
            ).execute_async()
            if not retry:
                logger.info("退出程序")
                exit(1)
                return

    logger.warning("请确保在抢床前已知晓抢床时间，系统会在开始时间到达时自动提交床位") 
    logger.warning('懒得写返回功能，请确保输入正确，不然重新登录吧')
    logger.info("开始获取宿舍信息")
    await api_client._get_drom_pos()
    area_list = api_client._generate_dorm_area_list()
    area_code = await inquirer.select(
        message="请选择宿舍区域",
        choices=[{'name': area['name'], 'value': area['code']} for area in area_list],
        validate=lambda x: x is not None or "必须选择一个区域"
    ).execute_async()
    floor_list = api_client._generate_drom_floor_list(area_code)
    floor_code = await inquirer.select(
        message="请选择楼层",
        choices=[{'name': floor['name'], 'value': floor['code']} for floor in floor_list],
        validate=lambda x: x is not None or "必须选择一个楼层"
    ).execute_async()
    room_list = api_client._generate_drom_room_list(floor_code)
    room_code = await inquirer.select(
        message="请选择房间",
        choices=[{'name': room['name'], 'value': room['code']} for room in room_list],
        validate=lambda x: x is not None or "必须选择一个房间"
    ).execute_async()
    bed_list = await api_client.get_bed_list(room_code)
    
    bed_id = await inquirer.select(
        message="请选择床位",
        choices=[{'name': bed['name'], 'value': bed['id']} for bed in bed_list],
        validate=lambda x: x is not None or "必须选择一个床位"
    ).execute_async()
    
    bedding_type = await api_client.get_bedding_type()
    beddingInfo = await inquirer.select(
        message="请选择被褥类型",
        choices=[{'name': bedding['name'], 'value': bedding['val']} for bedding in bedding_type],
        validate=lambda x: x is not None or "必须选择一个被褥类型"
    ).execute_async()

    await inquirer.confirm(
        message=f"您选择的床位ID为 {bed_id}，被褥类型为{beddingInfo}，是否确认提交？",
        default=True
    ).execute_async()

    begin_delta = await inquirer.text(
        message="请输入提早开始抢床时间（单位：秒）",
        default='0.5',
        validate=lambda x: x.isdigit() and int(x) >= 0 or "请输入一个非负数"
    ).execute_async()

    request_delta = await inquirer.text(
        message="请输入请求间隔时间（单位：秒）",
        default='0.1',
        validate=lambda x: x.isdigit() and float(x) > 0 or "请输入一个正数"
    ).execute_async()
    begin_delta = float(begin_delta)
    request_delta = float(request_delta)

    try:
        current_time = get_ntp_time()
        python_time = time.time()
        time_delta = current_time - python_time
        logger.info(f"当前 NTP 时间戳: {current_time}, Python 时间戳: {python_time}, 差值: {time_delta} 秒")
    except Exception as e:
        logger.error(f"获取 NTP 时间失败: {e}")
        time_delta = 0

    while True:
        try:
            start_time = api_client.get_start_time() / 1000
            current_time = time.time() + time_delta
            logger.debug(f"当前时间: {time.ctime(current_time)}, 开始时间: {time.ctime(start_time)}")
            time_diff = start_time - current_time
            # 转化为分钟
            time_diff_minutes = int(time_diff / 60)
            logger.debug(f"距离开始时间还有 {time_diff} 秒 ({time_diff_minutes} 分钟)")
            if time_diff_minutes > 60 * 24:
                logger.error("开始时间超过24小时，你抢你m呢？")
                await asyncio.sleep(60)
            elif time_diff_minutes > 10:
                logger.info(f"距离开始时间还有 {time_diff_minutes} 分钟，等待中...")
                await asyncio.sleep(60)
            elif time_diff_minutes > 1:
                logger.info(f"距离开始时间还有 {time_diff} 秒，准备提交床位...")
                await asyncio.sleep(10)
            elif time_diff > 5:
                logger.info(f"距离开始时间还有 {time_diff} 秒，准备提交床位...")
                await asyncio.sleep(1)
            elif time_diff > begin_delta:
                logger.info(f"距离开始时间还有 {time_diff} 秒，准备提交床位...")
                await asyncio.sleep(0.1)
            else:
                logger.info("开始时间已到，疯狂提交床位...")
                await api_client.submit_bed(bed_id, beddingInfo)
                await asyncio.sleep(request_delta)
            
        except Exception as e:
            logger.error(f"床位提交失败: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.error("程序被用户中断，退出程序")
        time.sleep(3)
        exit(0)