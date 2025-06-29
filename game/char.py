import os

from game.jobs import JOB_MAP, Job
from gui.app_controller import APP_CONTROLLER
from service.config_file import CONFIG_FILE, DEBUG_ACTIVE, ITEM_BUFF
from service.memory import MEMORY
from service.offsets import Offsets
from service.servers_file import SKILL_BUFF, SERVERS_FILE, STATUS_DEBUFF
from util.number import calculate_percent


class Char:

    def __init__(self):
        self.update()

    def reset(self):
        self.current_map = ""
        self.job_id = 0
        self.hp = 0
        self.hp_max = 0
        self.hp_percent = 0
        self.sp = 0
        self.sp_max = 0
        self.sp_percent = 0
        self.chat_bar_enabled = False
        self.raw_buffs = []
        self.buffs = []
        self.skill_buffs = []
        self.item_buffs = []
        self.status_debuff = []
        self.entity_list = []
        self.job = None
        self.abracadabra_skill = None

    def update(self):
        try:
            self.hp = MEMORY.process.read_int(MEMORY.hp_address)
            self.hp_max = MEMORY.process.read_int(MEMORY.hp_address + Offsets.MAX_HP)
            self.hp_percent = calculate_percent(self.hp, self.hp_max)
            self.sp = MEMORY.process.read_int(MEMORY.hp_address + Offsets.SP)
            self.sp_max = MEMORY.process.read_int(MEMORY.hp_address + Offsets.MAX_SP)
            self.sp_percent = calculate_percent(self.sp, self.sp_max)
            self.current_map = MEMORY.process.read_string(MEMORY.map_address)
            self.job_id = MEMORY.process.read_int(MEMORY.job_address)
            self.raw_buffs = self._get_buffs()
            self.buffs = self._get_id_buffs_all()
            self.skill_buffs = self._get_id_buffs(SKILL_BUFF)
            self.item_buffs = self._get_id_buffs(ITEM_BUFF)
            self.status_debuff = self._get_id_buffs(STATUS_DEBUFF)
            self.job = JOB_MAP.get(self.job_id, self.job_id)
            self.abracadabra_skill = MEMORY.process.read_int(MEMORY.abracadabra_address)
            self.chat_bar_enabled = MEMORY.process.read_bool(MEMORY.chat_address)
            self.monitoring_job_change_gui()
            self.entity_list = self._get_entity_list()
            if CONFIG_FILE.read(DEBUG_ACTIVE):
                APP_CONTROLLER.debug.emit(self.__str__())
        except BaseException:
            self.reset()

    def _get_entity_list(self):
        offset_base = MEMORY.process.read_uint(MEMORY.entity_list_address)
        world = MEMORY.process.read_uint(offset_base + Offsets.WORLD)
        entity_list = MEMORY.process.read_uint(world + Offsets.ENTITY_LIST)
        prev_entity = MEMORY.process.read_uint(entity_list + Offsets.PREV_ENTITY)
        entity = MEMORY.process.read_uint(prev_entity + Offsets.NEXT_ENTITY)
        entities = []
        while entity != 0:
            mob_id = MEMORY.process.read_uint(entity + Offsets.ENTITY_ID)
            # x_pos = MEMORY.process.read_uint(entity + Offsets.ENTITY_POS_X)
            # y_pos = MEMORY.process.read_uint(entity + Offsets.ENTITY_POS_Y)
            if mob_id > 1000:
                sprite_res = MEMORY.process.read_uint(entity + Offsets.ENTITY_SPRITE_RES)
                sprite_name = MEMORY.process.read_string(sprite_res + Offsets.SPRITE_NAME)
                sprite_name = sprite_name.strip("\\").replace(".spr", "")
                sprint_name = sprite_name.replace("_", " ").title()
                entities.append((mob_id, sprint_name))
            prev_entity = MEMORY.process.read_uint(prev_entity + Offsets.PREV_ENTITY)
            entity = MEMORY.process.read_uint(prev_entity + Offsets.NEXT_ENTITY)
        return entities

    def close_chat_bar(self):
        MEMORY.process.write_bool(MEMORY.chat_address, False)

    def _get_id_buffs_all(self):
        skill_buffs = []
        skill_buff_map = SERVERS_FILE.get_value(SKILL_BUFF)
        item_buff_map = SERVERS_FILE.get_value(ITEM_BUFF)
        status_debuff_map = SERVERS_FILE.get_value(STATUS_DEBUFF)
        for buff in self.raw_buffs:
            skill_buff = skill_buff_map.get(str(buff), None) or item_buff_map.get(str(buff), None) or status_debuff_map.get(str(buff), buff)
            skill_buffs.append(skill_buff)
        return skill_buffs

    def _get_id_buffs(self, resource):
        skill_buffs = []
        skills_map = SERVERS_FILE.get_value(resource)
        for buff in self.raw_buffs:
            skill_buff = skills_map.get(str(buff), None)
            if not skill_buff:
                continue
            skill_buffs.append(skill_buff)
        return skill_buffs

    def next_item_buff_to_use(self, list_items) -> bool:
        for item in list_items:
            if item.id not in self.item_buffs:
                return item
        return None

    def next_item_debuff_to_use(self, list_items) -> bool:
        items_to_use = []
        for item in list_items:
            for status in item.recover_status:
                if status in self.status_debuff:
                    items_to_use.append(item)
        if len(items_to_use) == 0:
            return None
        return sorted(items_to_use, key=lambda item: item.priority, reverse=True)[0]

    def next_skill_buff_to_use(self, list_buff) -> bool:
        buffs_to_use = []
        for job, buffs in list_buff.items():
            for buff in buffs:
                if buff.id not in self.skill_buffs:
                    buffs_to_use.append((job, buff.id, buff.priority))
        if len(buffs_to_use) == 0:
            return (None, None, None)
        return sorted(buffs_to_use, key=lambda x: x[2], reverse=True)[0]

    def monitoring_job_change_gui(self):
        if APP_CONTROLLER.job.id != JOB_MAP[self.job_id].id and isinstance(self.job, Job):
            APP_CONTROLLER.updated_job.emit(self.job)

    def _get_buffs(self):
        buffs = []
        buff_index = 0
        while True:
            buff = MEMORY.process.read_int(MEMORY.hp_address + Offsets.BUFF_LIST + (0x4 * buff_index))
            if buff == -1:
                break
            buffs.append(buff)
            buff_index += 1
        return buffs

    def __str__(self):
        return f"""
            HP: {self.hp}/{self.hp_max}
            SP: {self.sp}/{self.sp_max}
            JOB: {self.job}
            MAP: {self.current_map}
            BUFFS: {self.buffs}
            CHAT_BAR_ENABLED: {self.chat_bar_enabled}
            ABRACADABRA_SKILL: {self.abracadabra_skill}
            ENTITY_LIST: \n{"\n".join([f"\t\t{id} - {name}" for id, name in self.entity_list])}
        """
