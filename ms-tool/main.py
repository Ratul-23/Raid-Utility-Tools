import asyncio
import ctypes
import os
import sys
from collections.abc import Callable, Coroutine
from typing import Any

import keyboard
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qasync import QEventLoop
from themes import Themes
from utils import Utils
from wizwalker import XYZ, Client
from wizwalker.errors import HookAlreadyActivated


class HooksTab(QWidget):
    def __init__(self, utils: Utils, hooked_clients: list[Client]) -> None:
        super().__init__()
        self.utils: Utils = utils
        self.hooked_clients: list[Client] = hooked_clients

        # ----- Creating Layout ----- #
        self.hooks_group_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.hooks_group_layout)
        # --------------------------- #

        # ----- Creating Hooks Group ----- #
        self.hooks_group: QGroupBox = QGroupBox("Hooks")
        self.hooks_tab_layout: QVBoxLayout = QVBoxLayout()
        self.hooks_group.setLayout(self.hooks_tab_layout)
        # -------------------------------- #

        # ----- Rename Clients Button ----- #
        rename_clients_button: QPushButton = QPushButton("Rename Clients")

        rename_clients_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        rename_clients_button.setMinimumHeight(50)

        rename_clients_button.clicked.connect(lambda: asyncio.create_task(self.rename_clients_wrapper()))

        self.hooks_tab_layout.addWidget(rename_clients_button)
        # --------------------------------- #

        self.hooks_tab_layout.addStretch() # makes rename button go to top

        # ----- Available Clients Checkboxes ----- #
        self.hooks_checkboxes: QGroupBox = QGroupBox("Available Clients")
        self.hooks_checkboxes_layout: QVBoxLayout = QVBoxLayout()

        self.client_checkboxes: list[QCheckBox] = []
        QTimer.singleShot(0, lambda: asyncio.create_task(self.update_client_checkboxes()))

        self.hooks_checkboxes.setLayout(self.hooks_checkboxes_layout)
        self.hooks_tab_layout.addWidget(self.hooks_checkboxes)
        # ---------------------------------------- #

        # ----- Creating No Clients Found Label ----- #
        self.no_clients_found_label: QLabel = QLabel("No clients found.")
        self.hooks_checkboxes_layout.addWidget(self.no_clients_found_label)
        self.no_clients_found_label.hide()
        # ------------------------------------------- #

        # ----- Activate Hooks Button ----- #
        activate_hooks_button: QPushButton = QPushButton("Activate Hooks")

        activate_hooks_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        activate_hooks_button.setMinimumHeight(50)

        activate_hooks_button.clicked.connect(lambda: asyncio.create_task(self.activate_hooks_wrapper()))

        self.hooks_tab_layout.addWidget(activate_hooks_button)
        # --------------------------------- #

        # ----- Deactivate Hooks Button ----- #
        deactivate_hooks_button: QPushButton = QPushButton("Deactivate Hooks")

        deactivate_hooks_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        deactivate_hooks_button.setMinimumHeight(50)

        deactivate_hooks_button.clicked.connect(lambda: asyncio.create_task(self.deactivate_hooks_wrapper()))

        self.hooks_tab_layout.addWidget(deactivate_hooks_button)
        # ----------------------------------- #

        self.hooks_group_layout.addWidget(self.hooks_group)


    async def rename_clients_wrapper(self) -> None:
        print("[HOOKS] Rename Clients pressed.")
        self.utils.rename_clients()


    async def activate_hooks_wrapper(self) -> None:
        print("[HOOKS] Activate Hooks pressed.")

        clients_to_hook: list[Client] = []

        for client_checkbox in self.client_checkboxes:
            if client_checkbox.isChecked():
                client: Client = client_checkbox.property("client")
                clients_to_hook.append(client)

        for client in clients_to_hook:
            try:
                await self.utils.activate_hooks(client)
            except HookAlreadyActivated:
                pass

        for client in clients_to_hook:
            if client.process_id not in {hooked_client.process_id for hooked_client in self.hooked_clients}:
                self.hooked_clients.append(client)


    async def deactivate_hooks_wrapper(self) -> None:
        print("[HOOKS] Deactivate Hooks pressed.")

        for client_checkbox in self.client_checkboxes:
            if client_checkbox.isChecked():
                client: Client = client_checkbox.property("client")

                for hooked_client in self.hooked_clients:
                    if client == hooked_client:
                        self.hooked_clients.remove(client)

                await self.utils.deactivate_hooks(client)


    async def update_client_checkboxes(self) -> None:
        while True:
            clients: list[Client] = self.utils.get_open_clients()
            existing_processes: list[int] = [client_checkbox.property("client").process_id for client_checkbox in self.client_checkboxes]

            # Remove Client Checkboxes that don't exist
            for client_checkbox in self.client_checkboxes[:]:
                if client_checkbox.property("client").process_id not in [client.process_id for client in clients]:
                    self.hooks_checkboxes_layout.removeWidget(client_checkbox)
                    client_checkbox.deleteLater()
                    self.client_checkboxes.remove(client_checkbox)

            for client_checkbox in self.client_checkboxes:
                client_process_id: int = client_checkbox.property("client").process_id # process id that is stored

                for client in clients:
                    if client.process_id == client_process_id:
                        if client_checkbox.text() != client.title:
                            client_checkbox.setText(client.title)
                            client_checkbox.setProperty("client", client)

            # Create Client Checkboxes
            for client in clients:
                if client.process_id not in existing_processes:
                    client_checkbox: QCheckBox = QCheckBox(client.title)
                    client_checkbox.setProperty("client", client)
                    self.client_checkboxes.append(client_checkbox)
                    self.hooks_checkboxes_layout.addWidget(client_checkbox)

            if self.client_checkboxes:
                self.no_clients_found_label.hide()

            if not self.client_checkboxes:
                self.no_clients_found_label.show()

            await asyncio.sleep(1)


class ClientsTab(QWidget):
    def __init__(self, utils: Utils, hooked_clients: list[Client]) -> None:
        super().__init__()
        self.utils: Utils = utils
        self.hooked_clients: list[Client] = hooked_clients

        # ----- Creating Layout ----- #
        self.clients_group_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.clients_group_layout)
        # --------------------------- #

        # ----- Creating Clients Group ----- #
        self.clients_group: QGroupBox = QGroupBox("Clients")
        self.clients_tab_layout: QVBoxLayout = QVBoxLayout()
        self.clients_group.setLayout(self.clients_tab_layout)
        # ---------------------------------- #

        self.clients_group_layout.addWidget(self.clients_group)

        self.client_frames: dict[int, dict[str, Any]] = {}  # key: client.process_id (dict), value: QFrame

        QTimer.singleShot(0, lambda: asyncio.create_task(self.update_hooked_client_info()))


    async def update_hooked_client_info(self) -> None:
        while True:
            # Remove clients that are no longer hooked
            for client_process_id in list(self.client_frames.keys()):
                if all(client_process_id != client.process_id for client in self.hooked_clients):
                    client_frame_info: dict[str, Any] = self.client_frames.pop(client_process_id)
                    client_frame: QGroupBox = client_frame_info['frame']
                    self.clients_tab_layout.removeWidget(client_frame)
                    client_frame.deleteLater()

            # Add new hooked clients
            for client in self.hooked_clients:
                if client.process_id not in self.client_frames:
                    client_frame: QGroupBox = QGroupBox(client.title)
                    client_frame_layout: QVBoxLayout = QVBoxLayout()

                    level_label: QLabel = QLabel(f"Level: {await client.stats.reference_level()}")
                    health_label: QLabel = QLabel(f"Health: {await client.stats.current_hitpoints()}/{await client.stats.max_hitpoints()}")
                    mana_label: QLabel = QLabel(f"Mana: {await client.stats.current_mana()}/{await client.stats.max_mana()}")
                    energy_label: QLabel = QLabel(f"Energy: {await client.current_energy()}/{await client.stats.energy_max() + await client.stats.bonus_energy()}")
                    position_label: QLabel = QLabel(f"Position: {await client.body.position()}")
                    yaw_label: QLabel = QLabel(f"Yaw: {await client.body.yaw()}")

                    client_frame_layout.addWidget(level_label)
                    client_frame_layout.addWidget(health_label)
                    client_frame_layout.addWidget(mana_label)
                    client_frame_layout.addWidget(energy_label)
                    client_frame_layout.addWidget(position_label)
                    client_frame_layout.addWidget(yaw_label)

                    self.client_frames[client.process_id] = {
                        'frame': client_frame,
                        'labels': {
                            'level': level_label,
                            'health': health_label,
                            'mana': mana_label,
                            'energy': energy_label,
                            'position': position_label,
                            'yaw': yaw_label
                        }
                    }

                    client_frame.setLayout(client_frame_layout)
                    self.clients_tab_layout.addWidget(client_frame, alignment=Qt.AlignmentFlag.AlignTop)

                else:
                    client_labels: dict[str, QLabel] = self.client_frames[client.process_id]['labels']
                    client_labels['level'].setText(f"Level: {await client.stats.reference_level()}")
                    client_labels['health'].setText(f"Health: {await client.stats.current_hitpoints()}/{await client.stats.max_hitpoints()}")
                    client_labels['mana'].setText(f"Mana: {await client.stats.current_mana()}/{await client.stats.max_mana()}")
                    client_labels['energy'].setText(f"Energy: {await client.current_energy()}/{await client.stats.energy_max() + await client.stats.bonus_energy()}")
                    client_labels['position'].setText(f"Position: {await client.body.position()}")
                    client_labels['yaw'].setText(f"Yaw: {await client.body.yaw()}")

            await asyncio.sleep(1)


class OutsideTab(QWidget):
    def __init__(self, utils: Utils, hooked_clients: list[Client]) -> None:
        super().__init__()
        self.utils: Utils = utils
        self.hooked_clients: list[Client] = hooked_clients

        # ----- Creating Layout ----- #
        self.outside_group_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.outside_group_layout)
        # --------------------------- #

        # ----- Shrines Group ----- #
        shrines_group: QGroupBox = QGroupBox("Shrines")
        shrines_group_layout: QVBoxLayout = QVBoxLayout()
        shrines_grid: QGridLayout = QGridLayout()

        death_shrine_button: QPushButton = QPushButton("Death Shrine (NW)\nTeleport")
        death_shrine_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        death_shrine_button.clicked.connect(lambda: asyncio.create_task(self.death_shrine_teleport()))

        storm_shrine_button: QPushButton = QPushButton("Storm Shrine (N)\nTeleport")
        storm_shrine_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        storm_shrine_button.clicked.connect(lambda: asyncio.create_task(self.storm_shrine_teleport()))

        life_shrine_button: QPushButton = QPushButton("Life Shrine (NE)\nTeleport")
        life_shrine_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        life_shrine_button.clicked.connect(lambda: asyncio.create_task(self.life_shrine_teleport()))

        ice_shrine_button: QPushButton = QPushButton("Ice Shrine (SW)\nTeleport")
        ice_shrine_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        ice_shrine_button.clicked.connect(lambda: asyncio.create_task(self.ice_shrine_teleport()))

        myth_shrine_button: QPushButton = QPushButton("Myth Shrine (S)\nTeleport")
        myth_shrine_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        myth_shrine_button.clicked.connect(lambda: asyncio.create_task(self.myth_shrine_teleport()))

        fire_shrine_button: QPushButton = QPushButton("Fire Shrine (SE)\nTeleport")
        fire_shrine_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        fire_shrine_button.clicked.connect(lambda: asyncio.create_task(self.fire_shrine_teleport()))

        shrines_grid.addWidget(death_shrine_button, 0, 0)
        shrines_grid.addWidget(storm_shrine_button, 0, 1)
        shrines_grid.addWidget(life_shrine_button, 0, 2)
        shrines_grid.addWidget(ice_shrine_button, 1, 0)
        shrines_grid.addWidget(myth_shrine_button, 1, 1)
        shrines_grid.addWidget(fire_shrine_button, 1, 2)

        shrines_group_layout.addLayout(shrines_grid)
        shrines_group.setLayout(shrines_group_layout)
        self.outside_group_layout.addWidget(shrines_group)
        # ------------------------- #

        # ----- Intersections Group ----- #
        intersections_group: QGroupBox = QGroupBox("Intersections")
        intersections_group_layout: QHBoxLayout = QHBoxLayout()

        north_intersection_button: QPushButton = QPushButton("North\nTeleport")
        north_intersection_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        north_intersection_button.clicked.connect(lambda: asyncio.create_task(self.north_intersection_teleport()))

        east_intersection_button: QPushButton = QPushButton("East\nTeleport")
        east_intersection_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        east_intersection_button.clicked.connect(lambda: asyncio.create_task(self.east_intersection_teleport()))

        south_intersection_button: QPushButton = QPushButton("South\nTeleport")
        south_intersection_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        south_intersection_button.clicked.connect(lambda: asyncio.create_task(self.south_intersection_teleport()))

        west_intersection_button: QPushButton = QPushButton("West\nTeleport")
        west_intersection_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        west_intersection_button.clicked.connect(lambda: asyncio.create_task(self.west_intersection_teleport()))

        intersections_group_layout.addWidget(north_intersection_button)
        intersections_group_layout.addWidget(east_intersection_button)
        intersections_group_layout.addWidget(south_intersection_button)
        intersections_group_layout.addWidget(west_intersection_button)
        intersections_group.setLayout(intersections_group_layout)
        self.outside_group_layout.addWidget(intersections_group)
        # -------------------------------- #

        # ----- Mobs Group ----- #
        mobs_group: QGroupBox = QGroupBox("Mobs")
        mobs_group_layout: QVBoxLayout = QVBoxLayout()
        mobs_grid: QGridLayout = QGridLayout()

        doom_button: QPushButton = QPushButton("Doom Yaoguai (Death)\nTeleport")
        doom_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        doom_button.clicked.connect(lambda: asyncio.create_task(self.doom_yaoguai_teleport()))

        turmoil_button: QPushButton = QPushButton("Turmoil Yaoguai (Storm)\nTeleport")
        turmoil_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        turmoil_button.clicked.connect(lambda: asyncio.create_task(self.turmoil_yaoguai_teleport()))

        primeval_button: QPushButton = QPushButton("Primeval Yaoguai (Life)\nTeleport")
        primeval_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        primeval_button.clicked.connect(lambda: asyncio.create_task(self.primeval_yaoguai_teleport()))

        everwinter_button: QPushButton = QPushButton("Everwinter Yaoguai (Ice)\nTeleport")
        everwinter_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        everwinter_button.clicked.connect(lambda: asyncio.create_task(self.everwinter_yaoguai_teleport()))

        trickster_button: QPushButton = QPushButton("Trickster Yaoguai (Myth)\nTeleport")
        trickster_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        trickster_button.clicked.connect(lambda: asyncio.create_task(self.trickster_yaoguai_teleport()))

        infernal_button: QPushButton = QPushButton("Infernal Yaoguai (Fire)\nTeleport")
        infernal_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        infernal_button.clicked.connect(lambda: asyncio.create_task(self.infernal_yaoguai_teleport()))

        mobs_grid.addWidget(doom_button, 0, 0)
        mobs_grid.addWidget(turmoil_button, 0, 1)
        mobs_grid.addWidget(primeval_button, 0, 2)
        mobs_grid.addWidget(everwinter_button, 1, 0)
        mobs_grid.addWidget(trickster_button, 1, 1)
        mobs_grid.addWidget(infernal_button, 1, 2)

        mobs_group_layout.addLayout(mobs_grid)
        mobs_group.setLayout(mobs_group_layout)
        self.outside_group_layout.addWidget(mobs_group)
        # --------------------- #

        # ----- Essence Forge Group ----- #
        essence_forge_group: QGroupBox = QGroupBox("Essence Forge")
        essence_forge_group_layout: QHBoxLayout = QHBoxLayout()

        essence_forge_north_button: QPushButton = QPushButton("North\nTeleport")
        essence_forge_north_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        essence_forge_north_button.clicked.connect(lambda: asyncio.create_task(self.essence_forge_north_teleport()))

        essence_forge_east_button: QPushButton = QPushButton("East\nTeleport")
        essence_forge_east_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        essence_forge_east_button.clicked.connect(lambda: asyncio.create_task(self.essence_forge_east_teleport()))

        essence_forge_south_button: QPushButton = QPushButton("South\nTeleport")
        essence_forge_south_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        essence_forge_south_button.clicked.connect(lambda: asyncio.create_task(self.essence_forge_south_teleport()))

        essence_forge_west_button: QPushButton = QPushButton("West\nTeleport")
        essence_forge_west_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        essence_forge_west_button.clicked.connect(lambda: asyncio.create_task(self.essence_forge_west_teleport()))

        essence_forge_group_layout.addWidget(essence_forge_north_button)
        essence_forge_group_layout.addWidget(essence_forge_east_button)
        essence_forge_group_layout.addWidget(essence_forge_south_button)
        essence_forge_group_layout.addWidget(essence_forge_west_button)
        essence_forge_group.setLayout(essence_forge_group_layout)
        self.outside_group_layout.addWidget(essence_forge_group)
        # ------------------------------- #

        # ----- Miscellaneous Group ----- #
        misc_group: QGroupBox = QGroupBox("Miscellaneous")
        misc_group_layout: QHBoxLayout = QHBoxLayout()

        wisp_teleport_button: QPushButton = QPushButton("Wisp\nTeleport")
        wisp_teleport_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        wisp_teleport_button.clicked.connect(lambda: asyncio.create_task(self.wisp_teleport()))

        time_torch_teleport_button: QPushButton = QPushButton("Time Torch\nFreecam Teleport")
        time_torch_teleport_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        time_torch_teleport_button.clicked.connect(lambda: asyncio.create_task(self.time_torch_teleport()))

        misc_group_layout.addWidget(wisp_teleport_button)
        misc_group_layout.addWidget(time_torch_teleport_button)
        misc_group.setLayout(misc_group_layout)
        self.outside_group_layout.addWidget(misc_group)
        # -------------------------------- #


    async def north_intersection_teleport(self) -> None:
        print("[TELEPORTS] North Intersection pressed.")
        await self.utils.handle_basic_teleport(0.0, 5500.0, 210.490)


    async def east_intersection_teleport(self) -> None:
        print("[TELEPORTS] East Intersection pressed.")
        await self.utils.handle_basic_teleport(7000.0, -2350.0, 211.516)


    async def south_intersection_teleport(self) -> None:
        print("[TELEPORTS] South Intersection pressed.")
        await self.utils.handle_basic_teleport(-1250.0, -10000.0, 211.516)


    async def west_intersection_teleport(self) -> None:
        print("[TELEPORTS] West Intersection pressed.")
        await self.utils.handle_basic_teleport(-8000.0, -2300.0, 210.488)


    async def storm_shrine_teleport(self) -> None:
        print("[TELEPORTS] Storm Shrine (North) pressed.")
        await self.utils.handle_basic_teleport(2000.0, 11200.0, 211.516)


    async def life_shrine_teleport(self) -> None:
        print("[TELEPORTS] Life Shrine (North East) pressed.")
        await self.utils.handle_basic_teleport(10000.0, 3500.0, 231.175)


    async def fire_shrine_teleport(self) -> None:
        print("[TELEPORTS] Fire Shrine (South East) pressed.")
        await self.utils.handle_basic_teleport(10000.0, -7000.0, 230.445)


    async def myth_shrine_teleport(self) -> None:
        print("[TELEPORTS] Myth Shrine (South) pressed.")
        await self.utils.handle_basic_teleport(-3000.0, -15900.0, 231.804)


    async def ice_shrine_teleport(self) -> None:
        print("[TELEPORTS] Ice Shrine (South West) pressed.")
        await self.utils.handle_basic_teleport(-11000.0, -8000.0, 224.645)


    async def death_shrine_teleport(self) -> None:
        print("[TELEPORTS] Death Shrine (North West) pressed.")
        await self.utils.handle_basic_teleport(-11000.0, 2500.0, 229.305)


    async def doom_yaoguai_teleport(self) -> None:
        print("[TELEPORTS] Doom Yaoguai (Death) pressed.")
        await self.utils.mob_entity_teleport("GR_MS_Spider_BlackWidow_A_01_NC")


    async def turmoil_yaoguai_teleport(self) -> None:
        print("[TELEPORTS] Turmoil Yaoguai (Storm) pressed.")
        await self.utils.mob_entity_teleport("GR_MS_Dragon_Sky_A_01_NC")


    async def primeval_yaoguai_teleport(self) -> None:
        print("[TELEPORTS] Primeval Yaoguai (Life) pressed.")
        await self.utils.mob_entity_teleport("GR_MS_Treant_Base_A_01_NC")


    async def everwinter_yaoguai_teleport(self) -> None:
        print("[TELEPORTS] Everwinter Yaoguai (Ice) pressed.")
        await self.utils.mob_entity_teleport("GR_MS_Ghost_LostSoul_E_01_NC")


    async def trickster_yaoguai_teleport(self) -> None:
        print("[TELEPORTS] Trickster Yaoguai (Myth) pressed.")
        await self.utils.mob_entity_teleport("GR_MS_Colossus_Stone_A_01_NC")


    async def infernal_yaoguai_teleport(self) -> None:
        print("[TELEPORTS] Infernal Yaoguai (Fire) pressed.")
        await self.utils.mob_entity_teleport("GR_MS_Samoorai_Clay_A_01_NC")


    async def essence_forge_north_teleport(self) -> None:
        print("[TELEPORTS] Essence Forge North pressed.")
        await self.utils.handle_basic_teleport(0.0, 200.0, 204.203)


    async def essence_forge_east_teleport(self) -> None:
        print("[TELEPORTS] Essence Forge East pressed.")
        await self.utils.handle_basic_teleport(2300.0, -2300.0, 213.011)


    async def essence_forge_south_teleport(self) -> None:
        print("[TELEPORTS] Essence Forge South pressed.")
        await self.utils.handle_basic_teleport(-1350.0, -5000.0, 207.070)


    async def essence_forge_west_teleport(self) -> None:
        print("[TELEPORTS] Essence Forge West pressed.")
        await self.utils.handle_basic_teleport(-3600.0, -2300.0, 211.996)


    async def time_torch_teleport(self) -> None:
        print("[TELEPORTS] Time Torch Teleport pressed.")
        await self.utils.entity_freecam_teleport("Raid_MS_TimeTorch")


    async def wisp_teleport(self) -> None:
        print("[TELEPORTS] Wisp Teleport pressed.")
        await self.utils.wisp_teleport()


class DrumsTab(QWidget):
    def __init__(self, utils: Utils, hooked_clients: list[Client]) -> None:
        super().__init__()
        self.utils: Utils = utils
        self.hooked_clients: list[Client] = hooked_clients

        self.auto_drums_task: asyncio.Task[None] | None = None

        # ----- Creating Layout ----- #
        self.drums_group_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.drums_group_layout)
        # --------------------------- #

        # ----- Creating Drums Group ----- #
        self.drums_group: QGroupBox = QGroupBox("Drums")
        self.drums_tab_layout: QHBoxLayout = QHBoxLayout()

        self.drums_group.setLayout(self.drums_tab_layout)
        self.drums_group_layout.addWidget(self.drums_group)
        # --------------------------------- #

        # ----- Drum Teleport Button ----- #
        drum_teleport_button: QPushButton = QPushButton("Drum Teleport")

        drum_teleport_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        drum_teleport_button.clicked.connect(lambda: asyncio.create_task(self.drum_teleport()))

        self.drums_tab_layout.addWidget(drum_teleport_button)
        # -------------------------------- #

        # ----- Auto Drums Button ----- #
        auto_drums_button: QPushButton = QPushButton("Auto Drums")

        auto_drums_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        auto_drums_button.clicked.connect(lambda: asyncio.create_task(self.auto_drums()))

        self.drums_tab_layout.addWidget(auto_drums_button)
        # ---------------------------- #


    async def drum_teleport(self) -> None:
        print("[DRUMS] Drum Teleport pressed.")
        await self.utils.raid_drum_teleport()

    async def auto_drums(self) -> None:
        print("[DRUMS] Auto Drums pressed.")

        if not self.auto_drums_task:
            self.auto_drums_task = asyncio.create_task(self.utils.auto_raid_drums())
            await self.auto_drums_task
            self.auto_drums_task = None
            return

        if self.auto_drums_task:
            self.auto_drums_task.cancel()
            self.auto_drums_task = None


class ExperimentalTab(QWidget):
    def __init__(self, utils: Utils, hooked_clients: list[Client]) -> None:
        super().__init__()
        self.utils: Utils = utils
        self.hooked_clients: list[Client] = hooked_clients

        # ----- Creating Layout ----- #
        self.experimental_group_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.experimental_group_layout)
        # --------------------------- #

        # ----- Creating Experimental Group ----- #
        self.experimental_group: QGroupBox = QGroupBox("Minimap")
        self.experimental_tab_layout: QVBoxLayout = QVBoxLayout()

        self.experimental_group.setLayout(self.experimental_tab_layout)
        self.experimental_group_layout.addWidget(self.experimental_group)
        # --------------------------------------- #

        # ----- Toggle Minimap Button ----- #
        toggle_minimap_button: QPushButton = QPushButton("Toggle Minimap")

        toggle_minimap_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        toggle_minimap_button.clicked.connect(lambda: asyncio.create_task(self.toggle_minimap()))

        self.experimental_tab_layout.addWidget(toggle_minimap_button)
        # --------------------------------- #


    async def toggle_minimap(self) -> None:
        print("[EXPERIMENTAL] Toggle Minimap pressed.")
        for client in self.hooked_clients:
            await self.utils.toggle_minimap(client)


class UtilityTab(QWidget):
    def __init__(self, utils: Utils, hooked_clients: list[Client]) -> None:
        super().__init__()
        self.utils: Utils = utils
        self.hooked_clients: list[Client] = hooked_clients

        self.auto_dialogue_tasks: dict[Client, asyncio.Task[None]] = {}
        self.speedhack_tasks: dict[Client, asyncio.Task[None]] = {}
        self.freecam_task: asyncio.Task[XYZ | None] | None = None

        # ----- Creating Layout ----- #
        self.utility_group_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.utility_group_layout)
        # --------------------------- #

        # ----- Creating Utility Group ----- #
        self.utility_group: QGroupBox = QGroupBox("Utility")
        self.utility_tab_layout: QVBoxLayout = QVBoxLayout()

        self.utility_group.setLayout(self.utility_tab_layout)
        self.utility_group_layout.addWidget(self.utility_group)
        # ---------------------------------- #

        # ----- Speedhack Row ----- #
        speedhack_widget: QWidget = QWidget()
        speedhack_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        speedhack_row: QHBoxLayout = QHBoxLayout(speedhack_widget)
        speedhack_row.setContentsMargins(0, 0, 0, 0)

        speedhack_button: QPushButton = QPushButton("Toggle Speedhack")

        speedhack_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        speedhack_button.clicked.connect(lambda: asyncio.create_task(self.toggle_speedhack()))

        self.speedhack_spinbox: QDoubleSpinBox = QDoubleSpinBox()
        self.speedhack_spinbox.setRange(0.1, 100.0)
        self.speedhack_spinbox.setSingleStep(0.5)
        self.speedhack_spinbox.setDecimals(1)
        self.speedhack_spinbox.setValue(4.0)
        self.speedhack_spinbox.setSuffix("x")

        speedhack_row.addWidget(speedhack_button)
        speedhack_row.addWidget(self.speedhack_spinbox)

        self.utility_tab_layout.addWidget(speedhack_widget)
        # ------------------------- #

        # ----- Auto Dialogue Button ----- #
        auto_dialogue_button: QPushButton = QPushButton("Toggle Auto Dialogue")

        auto_dialogue_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        auto_dialogue_button.clicked.connect(lambda: asyncio.create_task(self.toggle_auto_dialogue()))

        self.utility_tab_layout.addWidget(auto_dialogue_button)
        # -------------------------------- #

        # ----- Freecam Button ----- #
        freecam_button: QPushButton = QPushButton("Toggle Freecam")

        freecam_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        freecam_button.clicked.connect(lambda: asyncio.create_task(self.toggle_freecam()))

        self.utility_tab_layout.addWidget(freecam_button)
        # -------------------------- #

        # ----- Freecam Teleport Button ----- #
        freecam_teleport_button: QPushButton = QPushButton("Freecam Teleport")

        freecam_teleport_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        freecam_teleport_button.clicked.connect(lambda: asyncio.create_task(self.handle_freecam_teleport()))

        self.utility_tab_layout.addWidget(freecam_teleport_button)
        # ---------------------------------- #

        # ----- XYZ Sync Button ----- #
        xyz_sync_button: QPushButton = QPushButton("XYZ Sync")

        xyz_sync_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        xyz_sync_button.clicked.connect(lambda: asyncio.create_task(self.handle_xyz_sync()))

        self.utility_tab_layout.addWidget(xyz_sync_button)
        # --------------------------- #

        # ----- Copy Position Button ----- #
        copy_position_button: QPushButton = QPushButton("Copy Position")

        copy_position_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        copy_position_button.clicked.connect(lambda: asyncio.create_task(self.handle_copy_position()))

        self.utility_tab_layout.addWidget(copy_position_button)
        # -------------------------------- #


    async def toggle_auto_dialogue(self) -> None:
        print("[UTILITY] Auto Dialogue pressed.")

        if not self.auto_dialogue_tasks:
            for client in self.hooked_clients:
                self.auto_dialogue_tasks[client] = asyncio.create_task(self.utils.handle_auto_dialogue(client))

            return

        if self.auto_dialogue_tasks:
            for client, auto_dialogue_task in self.auto_dialogue_tasks.items():
                auto_dialogue_task.cancel()

            self.auto_dialogue_tasks = {}


    async def toggle_speedhack(self) -> None:
        print("[UTILITY] Speedhack pressed.")

        if not self.speedhack_tasks:
            for client in self.hooked_clients:
                self.speedhack_tasks[client] = asyncio.create_task(self.utils.handle_speedhack(client, self.speedhack_spinbox.value() * 100))

            return

        if self.speedhack_tasks:
            for client, speedhack_task in self.speedhack_tasks.items():
                speedhack_task.cancel()

            self.speedhack_tasks = {}


    async def toggle_freecam(self) -> None:
        print("[UTILITY] Freecam pressed.")

        if not self.freecam_task:
            if self.hooked_clients:
                self.freecam_task = asyncio.create_task(self.utils.handle_freecam())
                return

        if self.freecam_task:
            self.freecam_task.cancel()
            self.freecam_task = None
            print("[TOGGLE] Freecam cancelled.")


    async def handle_freecam_teleport(self) -> None:
        print("[UTILITY] Freecam Teleport pressed.")

        if not self.freecam_task:
            print("[UTILITY] Freecam is not active.")

        if self.freecam_task:
            self.freecam_task.cancel()
            camera_pos: XYZ | None = await self.freecam_task
            self.freecam_task = None

            if camera_pos is not None:
                self.freecam_teleport_task: asyncio.Task[None] = asyncio.create_task(self.utils.freecam_teleport(camera_pos))


    async def handle_xyz_sync(self) -> None:
        print("[UTILITY] XYZ Sync pressed.")
        await self.utils.xyz_sync()

    async def handle_copy_position(self) -> None:
        print("[UTILITY] Copy Position pressed.")
        await self.utils.copy_position()


class ThemesTab(QWidget):
    def __init__(self, themes: Themes) -> None:
        super().__init__()
        self.themes: Themes = themes

        # ----- Creating Layout ----- #
        self.themes_tab_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.themes_tab_layout)
        # --------------------------- #

        # ----- Creating Main Themes Group ----- #
        self.main_themes_group: QGroupBox = QGroupBox("Main Themes")
        self.main_themes_group_layout: QVBoxLayout = QVBoxLayout()
        # -------------------------------------- #

        # ----- Creating Preset Themes Group ----- #
        self.preset_themes_group: QGroupBox = QGroupBox("Preset Themes")
        self.preset_themes_group_layout: QVBoxLayout = QVBoxLayout()
        # ---------------------------------------- #

        # ----- Default Theme Button ----- #
        default_theme_button_button: QPushButton = QPushButton("Default Theme")

        default_theme_button_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        default_theme_button_button.clicked.connect(self.enable_default_theme)

        self.main_themes_group_layout.addWidget(default_theme_button_button)
        # -------------------------------- #

        # ----- Custom Theme Button ----- #
        custom_theme_button_button: QPushButton = QPushButton("Custom Theme")

        custom_theme_button_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        custom_theme_button_button.clicked.connect(self.enable_custom_theme)

        self.main_themes_group_layout.addWidget(custom_theme_button_button)
        # ------------------------------- #

        # ----- Night Theme Button ----- #
        night_theme_button_button: QPushButton = QPushButton("Night Theme")

        night_theme_button_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        night_theme_button_button.clicked.connect(self.enable_night_theme)

        self.preset_themes_group_layout.addWidget(night_theme_button_button)
        # ------------------------------ #

        # ----- Celestia Theme Button ----- #
        celestia_theme_button_button: QPushButton = QPushButton("Celestia Theme")

        celestia_theme_button_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        celestia_theme_button_button.clicked.connect(self.enable_celestia_theme)

        self.preset_themes_group_layout.addWidget(celestia_theme_button_button)
        # --------------------------------- #

        # ----- Mooshu Theme Button ----- #
        mooshu_theme_button_button: QPushButton = QPushButton("Mooshu Theme")

        mooshu_theme_button_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        mooshu_theme_button_button.clicked.connect(self.enable_mooshu_theme)

        self.preset_themes_group_layout.addWidget(mooshu_theme_button_button)
        # ------------------------------ #

        self.main_themes_group.setLayout(self.main_themes_group_layout)
        self.preset_themes_group.setLayout(self.preset_themes_group_layout)

        self.themes_tab_layout.addWidget(self.main_themes_group)
        self.themes_tab_layout.addWidget(self.preset_themes_group)


    def enable_default_theme(self) -> None:
        print("[THEMES] Default theme enabled.")
        if window := self.window():
            window.setStyleSheet(self.themes.default)


    def enable_custom_theme(self) -> None:
        print("[THEMES] Custom theme enabled.")
        if window := self.window():
            window.setStyleSheet(self.themes.custom_theme)


    def enable_night_theme(self) -> None:
        print("[THEMES] Night theme enabled.")
        if window := self.window():
            window.setStyleSheet(self.themes.night)


    def enable_celestia_theme(self) -> None:
        print("[THEMES] Celestia theme enabled.")
        if window := self.window():
            window.setStyleSheet(self.themes.celestia)


    def enable_mooshu_theme(self) -> None:
        print("[THEMES] Mooshu theme enabled.")
        if window := self.window():
            window.setStyleSheet(self.themes.mooshu)


class MainWindow(QWidget):
    def __init__(self, loop: QEventLoop) -> None:
        super().__init__()
        self.loop: QEventLoop = loop

        self.hooked_clients: list[Client] = []
        self.utils: Utils = Utils()
        self.themes: Themes = Themes()

        self.always_on_top_config: bool = bool(self.utils.read_config()["always_on_top"])
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.always_on_top_config)

        self.enable_clients_tab: bool = bool(self.utils.read_config()["enable_clients_tab"])

        self.use_raid_theme: bool = bool(self.utils.read_config()["use_raid_theme"])

        if self.use_raid_theme:
            self.setStyleSheet(self.themes.mooshu)

        self.setWindowTitle("Blighted Veil Cheat Tool - Ratul")
        self.resize(800, 600)

        layout: QVBoxLayout = QVBoxLayout(self)

        tabs: QTabWidget = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.North)

        self.hooks_tab: HooksTab = HooksTab(self.utils, self.hooked_clients)

        if self.enable_clients_tab:
            self.clients_tab: ClientsTab = ClientsTab(self.utils, self.hooked_clients)

        self.outside_tab: OutsideTab = OutsideTab(self.utils, self.hooked_clients)
        self.drums_tab: DrumsTab = DrumsTab(self.utils, self.hooked_clients)
        self.experimental_tab: ExperimentalTab = ExperimentalTab(self.utils, self.hooked_clients)
        self.utility_tab: UtilityTab = UtilityTab(self.utils, self.hooked_clients)
        self.themes_tab: ThemesTab = ThemesTab(self.themes)

        tabs.addTab(self.hooks_tab, "Hooks")

        if self.enable_clients_tab:
            tabs.addTab(self.clients_tab, "Clients")

        tabs.addTab(self.outside_tab, "Outside")
        tabs.addTab(self.drums_tab, "Drums")
        tabs.addTab(self.experimental_tab, "Experimental")
        tabs.addTab(self.utility_tab, "Utility")
        tabs.addTab(self.themes_tab, "Themes")

        layout.addWidget(tabs)

        # Creating footer
        footers_layout: QHBoxLayout = QHBoxLayout()

        donation_link_label: QLabel = QLabel('<a href="https://www.buymeacoffee.com/lxghtend">Donate</a>')
        donation_link_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        credit_label: QLabel = QLabel('Made by Lxghtend (<a href="https://github.com/Lxghtend">https://github.com/Lxghtend</a>)')
        credit_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        donation_link_label.setOpenExternalLinks(True)
        credit_label.setOpenExternalLinks(True)

        footers_layout.addWidget(donation_link_label)
        footers_layout.addWidget(credit_label)

        layout.addLayout(footers_layout)

        self.start_keybinds()


    def start_keybinds(self) -> None:
        def run_threadsafe(coroutine: Coroutine[Any, Any, None]) -> None:
            asyncio.run_coroutine_threadsafe(coroutine, self.loop)

        config: dict[str, bool | str] = self.utils.read_config()
        keybinds: dict[str, Callable[[], Coroutine[Any, Any, None]]] = {
            str(config["handle_xyz_sync"]): self.utility_tab.handle_xyz_sync,
            str(config["toggle_auto_dialogue"]): self.utility_tab.toggle_auto_dialogue,
            str(config["toggle_speedhack"]): self.utility_tab.toggle_speedhack,
            str(config["toggle_freecam"]): self.utility_tab.toggle_freecam,
            str(config["handle_freecam_teleport"]): self.utility_tab.handle_freecam_teleport,
        }

        for keybind, function in keybinds.items():
            keyboard.add_hotkey(keybind, lambda func=function: run_threadsafe(func()))


class DisclaimerDialog(QDialog):
    def __init__(self, parent: MainWindow | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Disclaimer")
        self.setFixedSize(220, 150)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        layout: QVBoxLayout = QVBoxLayout()

        label: QLabel = QLabel("Please consider donating to\nsupport future development.")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        donate_button: QPushButton = QPushButton("Donate")
        donate_button.clicked.connect(self.open_donate)

        ok_button: QPushButton = QPushButton("Ok")
        ok_button.clicked.connect(self.accept)

        layout.addWidget(label)
        layout.addWidget(donate_button)
        layout.addWidget(ok_button)

        self.setLayout(layout)


    def open_donate(self) -> None:
        QDesktopServices.openUrl(QUrl("https://buymeacoffee.com/lxghtend"))


def main() -> None:
    app: QApplication = QApplication(sys.argv)

    appid: str = "lxghtend.ms.tool.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)

    app.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "icon.ico")))

    app.setStyle("Fusion")

    loop: QEventLoop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window: MainWindow = MainWindow(loop)
    window.show()

    disclaimer: DisclaimerDialog = DisclaimerDialog(window)
    disclaimer.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
