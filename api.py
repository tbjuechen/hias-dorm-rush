import httpx
import uuid
from PIL import Image
from io import BytesIO
from Crypto.Cipher import AES
import base64
import time
import json
from loguru import logger
from term_image.image import AutoImage


class API:
    def __init__(self, personsn: str, password: str):
        self.personsn = personsn
        self.password = password
        self.uuid = None
        self.devideId = None
        self.token = None
        self.session = httpx.AsyncClient(headers={
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Content-Type": "application/json; charset=UTF-8",
            "Host": "apartment.hiaskc.com",
            "Origin": "http://apartment.hiaskc.com",
            "Proxy-Connection": "keep-alive",
            "Referer": "http://apartment.hiaskc.com/wxweb/",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        })

    async def _get_vertification_code(self):
        self.uuid = str(uuid.uuid1())
        api_url = 'http://apartment.hiaskc.com/appsys/captcha.png'
        response = await self.session.get(api_url, params={'uuid': self.uuid})
        response.raise_for_status()
        try:
            image = Image.open(BytesIO(response.content))
            image = AutoImage(image)
            image.draw(alpha='#ffffff', pad_height=16)
        except Exception as e:
            print(f"Error opening image: {e}")

    async def login(self, input_code: str = '1'):
        api_url = 'http://apartment.hiaskc.com/appsys/app/login'
        self.session.headers.update({'token': ''})
        data = {
            'username': self.personsn,
            'password': self.encrypt_aes_ecb_base64(self.password, 'shuangqibestbest'),
            'captcha': input_code,
            'uuid': self.uuid,
            't': int(time.time() * 1000)
        }
        logger.debug(f"构造登录载荷: {data}")
        response = await self.session.post(api_url, json=data)
        res = response.json()
        logger.debug(f"登录响应: {res}")
        assert response.status_code == 200 and res.get('code') == 0, "Login failed"
        self.token = res['token']
        self.sqcode = res['sqcode']
        self.session.headers.update({'token': self.token})
        await self._get_divideID()
        return True

    async def _get_divideID(self):
        api_url = 'http://apartment.hiaskc.com/appdm/freshman/resident/getDivideCountDown'
        params = {
            't': int(time.time() * 1000),
            'personsn': self.personsn,
            'status': 'WX'
        }
        logger.debug(f"获取分配ID的参数: {params}")
        response = await self.session.get(api_url, params=params)
        res = response.json()
        logger.debug(f"获取分配ID的响应: {res}")
        self.start_time = res['divideCountDown']['start']
        self.devideId = res['divideCountDown']['id']

    @staticmethod
    def pad_pkcs7(s: bytes) -> bytes:
        bs = AES.block_size
        padding_len = bs - len(s) % bs
        return s + bytes([padding_len] * padding_len)

    @staticmethod
    def encrypt_aes_ecb_base64(plain_text: str, key: str) -> str:
        key_bytes = key.encode('utf-8')
        data = plain_text.encode('utf-8')
        cipher = AES.new(key_bytes, AES.MODE_ECB)
        padded = API.pad_pkcs7(data)
        encrypted = cipher.encrypt(padded)
        return base64.b64encode(encrypted).decode('utf-8')

    async def _get_drom_pos(self):
        api_url = 'http://apartment.hiaskc.com/appdm/freshman/divide/getBunkByDivideId'
        params = {
            'divideId': self.devideId,
            't': int(time.time() * 1000)
        }
        response = await self.session.get(api_url, params=params)
        res = response.json()
        self.dorm_pos = res['freshmanDisplayBunkVos'][0]['children'][0]['children'][0]['children']

    def _generate_dorm_area_list(self):
        return [{'name': item['name'], 'code': item['code']} for item in self.dorm_pos]

    def _generate_drom_floor_list(self, area_code: str):
        self.current_area_code = area_code
        area_info = next((item for item in self.dorm_pos if item['code'] == area_code), None)
        self.current_floor_list = area_info['children'][0]['floorList']
        return [{'name': item['name'], 'code': item['code']} for item in self.current_floor_list]

    def _generate_drom_room_list(self, floor_code: str):
        self.current_floor_code = floor_code
        floor_info = next((item for item in self.current_floor_list if item['code'] == floor_code), None)
        self.current_room_list = floor_info['suiteList'][0]['roomList']
        return [{'name': item['name'], 'roomInfo': '4人间', 'code': item['code']} for item in self.current_room_list]

    async def get_bed_list(self, room_code: str):
        api_url = 'http://apartment.hiaskc.com/appdm/freshman/divide/getBedInfoForRoomByDivideId'
        params = {
            'divideId': self.devideId,
            't': int(time.time() * 1000),
            'code': room_code
        }
        response = await self.session.post(api_url, params=params)
        res = response.json()
        logger.debug(f"获取床位列表响应: {res}")
        self.current_bed_list = res['bedList']
        return [{'name': bed['name'], 'id': bed['id']} for bed in self.current_bed_list]

    async def submit_bed(self, bed_id: str, beddingInfo: str = '01'):
        api_url = 'http://apartment.hiaskc.com/appdm/freshman/bunk/distributeBed'
        timestamp = int(time.time() * 1000)
        data = {
            't': timestamp,
            'divideId': self.devideId,
            'aircondition': '',
            'chooseWay': 1,
            'personsn': self.personsn,
            'beddingInfo': beddingInfo,
            'bedPlaceCode': self.encrypt_aes_ecb_base64(bed_id, f'shu{str(timestamp)}'),
        }
        logger.debug(f"提交床位的载荷: {data}")
        response = await self.session.post(api_url, json=data, timeout=2)
        res = response.json()
        logger.debug(f"提交床位的响应: {res}")
        return res

    def get_start_time(self):
        return self.start_time

    async def get_bedding_type(self):
        api_url = 'http://apartment.hiaskc.com/appdm/bedding/beddinginfo/group'
        params = {
            't': int(time.time() * 1000),
            'divideId': self.devideId,
        }
        response = await self.session.get(api_url, params=params)
        res = response.json()
        logger.debug(f"获取被褥类型: {res}")
        self.properties = res['group']['properties']
        return self.properties[0]['v']
    
    @staticmethod
    def _generate_baddinginfo(json_data):
        bedding_info = []

        for prop in json_data:
            selected_values = [
                item["val"] for item in prop["v"]
                if item["index"] == prop["defaultIndex"]
            ]
            bedding_info.append([prop["k_id"], selected_values])

        # 转成 JSON 字符串
        bedding_info_str = json.dumps(bedding_info, ensure_ascii=False)
        return bedding_info_str
    
    async def save_bed(self, bedPlaceCode: str):
        api_url = 'http://apartment.hiaskc.com/appdm/freshman/collect/saveBed'
        bedCodes = []
        for bed in self.current_bed_list:
            bedCodes.append(bed['id'])
        data = {
            'bedCodes': ','.join(bedCodes),
            'bedPlaceCode': bedPlaceCode,
            'personsn': self.personsn,
            't': int(time.time() * 1000),
            'divideId': self.devideId,
            'beddingInfo': self._generate_baddinginfo(self.properties)
        }
        logger.debug(f"构造保存床位的载荷: {json.dumps(data, ensure_ascii=False)}")
        response = await self.session.post(api_url, json=data)
        res = response.json()
        logger.debug(f"保存床位的响应: {res}")
        assert response.status_code == 200 and res.get('code') == 0, "Save bed failed" 
        return True
    
    async def get_bed_collection(self):
        api_url = 'http://apartment.hiaskc.com/appdm/freshman/collect/getBedCollectList'
        params = {
            't': int(time.time() * 1000),
            'divideId': self.devideId,
            'personsn': self.personsn,
            'modelId': 'dm'
        }
        logger.debug(f"获取床位收藏列表的载荷: {params}")
        res = await self.session.post(api_url, params=params)
        res = res.json()
        logger.debug(f"获取床位收藏列表的响应: {res}")
        assert res.get('code') == 0, "获取床位收藏列表失败"
        self.bedCollects = res['bedCollects']
        return self.bedCollects
    
    async def delete_bed(self, bed_id: str, bed_code: str):
        api_url = 'http://apartment.hiaskc.com/appdm/freshman/collect/deleteBedCollect'
        params = {
            't': int(time.time() * 1000),
            'id': bed_id,
            'bedCode': bed_code
        }
        logger.debug(f"删除床位收藏的载荷: {params}")
        response = await self.session.post(api_url, params=params)
        res = response.json()
        logger.debug(f"删除床位收藏的响应: {res}")
        assert res.get('code') == 0, "删除床位收藏成功"

    async def delete_all_bed(self):
        await self.get_bed_collection()
        if not self.bedCollects:
            logger.warning("没有床位收藏，无法删除")
            return
        for bed in self.bedCollects:
            await self.delete_bed(bed['id'], bed['code'])
            await asyncio.sleep(2)
        logger.info("所有床位收藏已删除")
    
import asyncio

async def test():
    api = API('2025E8021682038', '06132715')
    api._get_vertification_code()
    await api.login('1')
    
    #
    # 注意：以下代码是用于获得用户所有床位信息
    # 仅供参考，实际使用时请根据需要调整
    # 代码存在问题，在第二轮遍历时调用save_bed时
    # 会提交同样的bed_code, 应该是没有更新self.current_bed_list的问题
    # 会导致查看收藏api返回的异常，要打电话给公司
    # 在没有能力修复的情况下，请不要使用下面的代码
    #

    # await api._get_drom_pos()
    # area_list = api._generate_dorm_area_list()
    # save_count = 0
    # await api.delete_all_bed()
    # await api.get_bedding_type()
    # bed_list = []
    # for area in area_list:
    #     floor_list = api._generate_drom_floor_list(area['code'])
    #     for floor in floor_list:
    #         room_list = api._generate_drom_room_list(floor['code'])
    #         for room in room_list:
    #             bed_list = await api.get_bed_list(room['code'])
    #             for bed in bed_list:
    #                 await api.save_bed(bed['id'])
    #                 save_count += 1
    #                 if save_count % 5 == 0:
    #                     res = await api.get_bed_collection()
    #                     for item in res:
    #                         bed_list.append({
    #                             'name': item['name'],
    #                             'id': item['id'],
    #                             'code': item['code'],
    #                             'address': item['address']
    #                         })
    #                         print(bed_list[-1])
    #                     await asyncio.sleep(2)
    #                     await api.delete_all_bed()
    #                 await asyncio.sleep(2)
    
if __name__ == "__main__":
    asyncio.run(test())
