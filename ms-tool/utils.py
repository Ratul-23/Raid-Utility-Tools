import asyncio
import configparser
import threading
import time

import pyperclip
from wizwalker import XYZ, Client, ClientHandler
from wizwalker.constants import Keycode, Primitive
from wizwalker.errors import HookNotActive, MemoryWriteError
from wizwalker.memory import Window
from wizwalker.memory.memory_objects.camera_controller import (
    DynamicFreeCameraController,
)
from wizwalker.memory.memory_objects.client_object import DynamicClientObject
from wizwalker.memory.memory_objects.enums import WindowFlags
from wizwalker.memory.memory_objects.window import DynamicWindow
from worlds_collide import WorldsCollideTP

excluded_drums: list[XYZ] = [
    XYZ(-3.070, -900.000, 680.000),
    XYZ(-126.960, -900.000, 680.000),
    XYZ(117.797, -900.000, 680.000),
    XYZ(-249.350, -900.000, 680.000),
    XYZ(-993.921, -900.000, 680.000),
    XYZ(-1113.587, -900.000, 680.000),
    XYZ(-1232.520, -900.000, 680.000),
    XYZ(-1351.739, -900.000, 679.999),
]


class Utils():
    def __init__(self) -> None:
        self.handler: ClientHandler = ClientHandler()
        self.config_parser: configparser.ConfigParser = configparser.ConfigParser()
        self.foreground_client: Client | None = None

        threading.Thread(target=self.update_foreground_client, daemon=True).start()
        threading.Thread(target=lambda: asyncio.run(self.update_hooked_text()), daemon=True).start()


    def update_foreground_client(self) -> None:
        while True:
            if (client := self.handler.get_foreground_client()):
                self.foreground_client = client

            time.sleep(0.1)


    async def update_hooked_text(self) -> None:
        async def write_window_rectangle(window: Window, x1: int, y1: int, x2: int, y2: int) -> None:
            await window.write_value_to_offset(160, x1, Primitive.int32)
            await window.write_value_to_offset(164, y1, Primitive.int32)
            await window.write_value_to_offset(168, x2, Primitive.int32)
            await window.write_value_to_offset(172, y2, Primitive.int32)

        while True:
            for client in self.get_open_clients():
                try:
                    window: DynamicWindow = (await client.root_window.get_windows_with_name('txtTestRealmText'))[0]
                    await write_window_rectangle(window, 10, 146, 153, 165)
                    await window.write_maybe_text('HOOKED')
                    await window.write_flags(WindowFlags.visible)

                except (IndexError, HookNotActive, MemoryWriteError):
                    pass

            await asyncio.sleep(1)


    def read_config(self) -> dict[str, bool | str]:
        settings: dict[str, bool | str] = {}
        self.config_parser.read("config.ini")

        # [General]
        settings["always_on_top"] = self.config_parser.getboolean("General", "always_on_top", fallback=True)
        settings["enable_clients_tab"] = self.config_parser.getboolean("General", "enable_clients_tab", fallback=True)
        settings["use_raid_theme"] = self.config_parser.getboolean("General", "use_raid_theme", fallback=True)

        # [Keybinds]
        settings["handle_xyz_sync"] = self.config_parser.get("Keybinds", "handle_xyz_sync", fallback="F3")
        settings["toggle_speedhack"] = self.config_parser.get("Keybinds", "toggle_speedhack", fallback="F4")
        settings["toggle_freecam"] = self.config_parser.get("Keybinds", "toggle_freecam", fallback="F5")
        settings["handle_freecam_teleport"] = self.config_parser.get("Keybinds", "handle_freecam_teleport", fallback="F6")
        settings["toggle_auto_dialogue"] = self.config_parser.get("Keybinds", "toggle_auto_dialogue", fallback="F7")

        return settings


    async def is_visible_by_path(self, base_window: Window, path: list[str]) -> bool:
        if window := await self.window_from_path(base_window, path):
            return await window.is_visible()

        return False


    async def window_from_path(self, base_window: Window, path: list[str]) -> Window | None:
        if not path:
            return base_window

        for child in await base_window.children():
            if await child.name() == path[0]:
                if found_window := await self.window_from_path(child, path[1:]):
                    return found_window

        return None


    def are_xyzs_within_threshold(self, xyz_1: XYZ, xyz_2: XYZ, threshold: int = 200) -> bool:
    # checks if 2 xyz's are within a rough distance threshold of each other. Not actual distance checking, but precision isn't needed for this, this exists to eliminate tiny variations in XYZ when being sent back from a failed port.
        threshold_check: list[bool] = [abs(abs(xyz_1.x) - abs(xyz_2.x)) < threshold, abs(abs(xyz_1.y) - abs(xyz_2.y)) < threshold, abs(abs(xyz_1.z) - abs(xyz_2.z)) < threshold]
        return all(threshold_check)


    def get_open_clients(self) -> list[Client]:
        self.handler.remove_dead_clients()
        clients: list[Client] = self.handler.get_new_clients()

        if not clients:
            clients = self.handler.get_ordered_clients()

        return clients


    def rename_clients(self) -> None:
        clients: list[Client] = self.handler.get_new_clients()

        if not clients:
            clients = self.handler.get_ordered_clients()

        for i, client in enumerate(clients, 1):
            client.title = "Client: " + str(i)


    async def activate_hooks(self, client: Client) -> None:
        await client.activate_hooks()
        print(f"{client.title} hooks activated.")


    async def deactivate_hooks(self, client: Client) -> None:
        # hooked_window: DynamicWindow = (await client.root_window.get_windows_with_name('txtTestRealmText'))[0]
        # await hooked_window.write_flags(WindowFlags.disabled)
        await client.close()
        print(f"{client.title} hooks deactivated.")


    async def handle_auto_dialogue(self, client: Client) -> None:
        try:
            print(f"{client.title} auto dialogue activated.")

            while True:
                if await self.is_visible_by_path(client.root_window, ['WorldView', 'wndDialogMain', 'btnRight']):
                    await client.send_key(Keycode.SPACEBAR)

                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            print(f"{client.title} auto dialogue deactivated.")


    async def handle_speedhack(self, client: Client, multiplier: float) -> None:
        try:
            print(f"{client.title} speedhack activated at {multiplier / 100:g}x.")

            while True:
                await client.client_object.write_speed_multiplier(round(multiplier))
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            await client.client_object.write_speed_multiplier(1)
            print(f"{client.title} speedhack deactivated.")


    async def handle_freecam(self) -> XYZ | None:
        client: Client | None = self.foreground_client

        if client:
            try:
                while True:
                    if not await client.game_client.is_freecam():
                        await client.camera_freecam()
                        print("[TOGGLE] Freecam started.")

                    await asyncio.sleep(0)

            except asyncio.CancelledError:
                if camera := await client.game_client.free_camera_controller():
                    camera_pos: XYZ = await camera.position()
                    await client.camera_elastic()
                    return camera_pos

        return None


    async def freecam_teleport(self, camera_pos: XYZ) -> None:
        client: Client | None = self.foreground_client

        if client:
            await client.teleport(camera_pos, wait_on_inuse=True, purge_on_after_unuser_fixer=True)
            print(f"{client.title} teleported to freecam position.")


    async def xyz_sync(self) -> None:
        client: Client | None = self.foreground_client

        if client:
            client_position: XYZ = await client.body.position()

            for teleporting_client in self.handler.get_ordered_clients():
                if teleporting_client is not client:
                    await teleporting_client.teleport(client_position)


    async def copy_position(self) -> None:
        client: Client | None = self.foreground_client

        if client:
            current_pos: XYZ = await client.body.position()
            print(f"{client.title} copied current position at {current_pos}.")
            pyperclip.copy(f'XYZ({current_pos.x}, {current_pos.y}, {current_pos.z})')


    async def handle_basic_teleport(self, location_x: float, location_y: float, location_z: float, yaw: float | None = None) -> None:
        client: Client | None = self.foreground_client

        if client:
            if yaw is not None:
                await client.teleport(XYZ(location_x, location_y, location_z), yaw)
            else:
                await client.teleport(XYZ(location_x, location_y, location_z))


    async def wisp_teleport(self) -> None:
        client: Client | None = self.foreground_client

        if client:
            entities: list[DynamicClientObject] = await client.get_base_entities_with_name("Raid_MS_Shadow_Wisp_01")

            if not entities:
                print(f"{client.title} did not find Raid_MS_Shadow_Wisp_01.")
                return

            original_location: XYZ = await client.body.position()
            await WorldsCollideTP(client, await entities[0].location())
            await asyncio.sleep(2)
            await client.teleport(original_location)
            print(f"{client.title} wisp teleport complete.")


    async def entity_teleport(self, entity_name: str) -> None:
        client: Client | None = self.foreground_client

        if client:
            entity: list[DynamicClientObject] = await client.get_base_entities_with_name(entity_name)

            if not entity:
                print(f"{client.title} did not find {entity_name}")
                return

            await WorldsCollideTP(client, await entity[0].location())
            print(f"{client.title} teleported to {entity_name}.")


    async def mob_entity_teleport(self, entity_name: str) -> None:
        client: Client | None = self.foreground_client

        if client:
            entity: list[DynamicClientObject] = await client.get_base_entities_with_name(entity_name)

            if not entity:
                print(f"{client.title} did not find {entity_name}")
                return

            entity_pos: XYZ = await entity[0].location()

            if entity_pos.z <= 200.0:
                return

            await WorldsCollideTP(client, entity_pos)
            print(f"{client.title} teleported to {entity_name}.")


    async def entity_freecam_teleport(self, entity_name: str) -> None:
        client: Client | None = self.foreground_client

        if client:
            if not await client.game_client.is_freecam():
                print(f"{client.title} is not in freecam.")
                return

            entities: list[DynamicClientObject] = await client.get_base_entities_with_name(entity_name)
            entity: DynamicClientObject | None = entities[0] if entities else None

            camera: DynamicFreeCameraController | None = await client.game_client.free_camera_controller()

            if entity and camera:
                await camera.write_position(await entity.location())
                print(f"{client.title} camera teleported to {entity_name}.")


    async def grab_item(self, entity_name: str) -> None:
        client: Client | None = self.foreground_client

        if client:
            original_location: XYZ = await client.body.position()
            item: list[DynamicClientObject] = await client.get_base_entities_with_name(entity_name)

            if not item:
                print(f"{client.title} did not find {entity_name}.")
                return

            item_position: XYZ = await item[0].location()
            await WorldsCollideTP(client, item_position)
            await asyncio.sleep(0.1)

            if await client.body.position() == original_location:
                return

            while not await self.is_visible_by_path(client.root_window, ['WorldView', 'NPCRangeWin', 'wndTitleBackground']):
                if await client.body.position() == original_location:
                    break

                await asyncio.sleep(0.1)

            while True:
                if not await self.is_visible_by_path(client.root_window, ['WorldView', 'NPCRangeWin', 'wndTitleBackground']):
                    break

                await client.send_key(Keycode.X, 0.1)
                await asyncio.sleep(0.1)

            if await client.body.position() != original_location:
                await client.teleport(original_location)

            print(f"{client.title} grabbed {entity_name}.")


    async def raid_drum_teleport(self) -> None:
        client: Client | None = self.foreground_client

        if client:
            drum_list: list[DynamicClientObject] = await client.get_base_entities_with_name("Raid_LightPad")

            if not drum_list:
                print(f"{client.title} did not find Raid_LightPad.")
                return

            filtered_drums: list[DynamicClientObject] = []

            for drum in drum_list:
                drum_pos: XYZ = await drum.location()
                if not any(self.are_xyzs_within_threshold(drum_pos, excluded) for excluded in excluded_drums):
                    filtered_drums.append(drum)

            if len(filtered_drums) > 0:
                drum: DynamicClientObject = filtered_drums[0]
                await client.teleport(await drum.location())


    async def toggle_minimap(self, client: Client) -> None:
        windows: list[DynamicWindow] = await client.root_window.get_windows_with_type("BattlegroundMiniMapWindow")

        if not windows:
            print(f"{client.title} minimap window not found.")
            return

        minimap_window: DynamicWindow = windows[0]
        curr_flags: WindowFlags = await minimap_window.flags()
        await minimap_window.write_flags(curr_flags ^ WindowFlags(WindowFlags.visible) ^ WindowFlags(WindowFlags.disabled))
        print(f"{client.title} minimap toggled.")


    async def auto_raid_drums(self) -> None:
        client: Client | None = self.foreground_client

        if client:
            try:
                for i in range(8):
                    filtered_drums: list[DynamicClientObject] = []

                    while filtered_drums == []:
                        drum_list: list[DynamicClientObject] = await client.get_base_entities_with_name("Raid_LightPad")

                        for drum in drum_list:
                            drum_pos: XYZ = await drum.location()

                            if not any(self.are_xyzs_within_threshold(drum_pos, excluded) for excluded in excluded_drums):
                                filtered_drums.append(drum)

                        await asyncio.sleep(0.1)

                    target_drum: DynamicClientObject = filtered_drums[0]
                    target_drum_gid: int = await target_drum.global_id_full()
                    await client.teleport(await target_drum.location())

                    while True:
                        current_drums: list[DynamicClientObject] = await client.get_base_entities_with_name("Raid_LightPad")
                        current_drum_gids: list[int] = [await drum.global_id_full() for drum in current_drums]

                        if target_drum_gid not in current_drum_gids:
                            break

                        await asyncio.sleep(0.1)

                    print(f"{client.title} activated drum {i + 1}.")

                print("[AUTO DRUMS] completed drums.")

            except asyncio.CancelledError:
                print(f"[AUTO DRUMS] cancelled at drum #{i + 1}.")
