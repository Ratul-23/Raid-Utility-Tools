import asyncio
import ctypes
import os
import sys
from collections.abc import Callable, Coroutine
from typing import Any

import keyboard
from PyQt6.QtCore import QRect, QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon, QPainter, QPalette
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
    QStyle,
    QStyleOptionButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qasync import QEventLoop
from themes import Themes
from utils import Utils
from wizwalker import XYZ, Client
from wizwalker.errors import HookAlreadyActivated


class WrapButton(QPushButton):
    def minimumSizeHint(self) -> QSize:
        return QSize(1, 1)

    def paintEvent(self, a0) -> None:
        style = self.style()

        if style is None:
            return

        painter = QPainter(self)
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        opt.text = ""

        style.drawControl(QStyle.ControlElement.CE_PushButton, opt, painter, self)
        self.initStyleOption(opt)
        text_rect: QRect = style.subElementRect(QStyle.SubElement.SE_PushButtonContents, opt, self)

        style.drawItemText(
            painter,
            text_rect,
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self.palette(),
            self.isEnabled(),
            self.text(),
            QPalette.ColorRole.ButtonText,
        )


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
        rename_clients_button = WrapButton("Rename Clients")

        rename_clients_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        rename_clients_button.setMinimumHeight(50)

        rename_clients_button.clicked.connect(lambda: asyncio.create_task(self.rename_clients_wrapper()))

        self.hooks_tab_layout.addWidget(rename_clients_button)
        # --------------------------------- #

        self.hooks_tab_layout.addStretch()  # makes rename button go to top

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
        activate_hooks_button = WrapButton("Activate Hooks")
        activate_hooks_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        activate_hooks_button.setMinimumHeight(50)
        activate_hooks_button.clicked.connect(lambda: asyncio.create_task(self.activate_hooks_wrapper()))
        self.hooks_tab_layout.addWidget(activate_hooks_button)
        # --------------------------------- #

        # ----- Deactivate Hooks Button ----- #
        deactivate_hooks_button = WrapButton("Deactivate Hooks")
        deactivate_hooks_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        deactivate_hooks_button.setMinimumHeight(50)
        deactivate_hooks_button.clicked.connect(lambda: asyncio.create_task(self.deactivate_hooks_wrapper()))
        self.hooks_tab_layout.addWidget(deactivate_hooks_button)
        # ----------------------------------- #

        self.hooks_group_layout.addWidget(self.hooks_group)

    async def rename_clients_wrapper(self) -> None:
        print("[HOOKS] Rename Clients pressed")
        self.utils.rename_clients()

    async def activate_hooks_wrapper(self) -> None:
        print("[HOOKS] Activate Hooks pressed")

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
        print("[HOOKS] Deactivate Hooks pressed")

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
            existing_processes: list[int] = [
                client_checkbox.property("client").process_id for client_checkbox in self.client_checkboxes
            ]

            # Remove Client Checkboxes that don't exist
            for client_checkbox in self.client_checkboxes[:]:
                if client_checkbox.property("client").process_id not in [client.process_id for client in clients]:
                    self.hooks_checkboxes_layout.removeWidget(client_checkbox)
                    client_checkbox.deleteLater()
                    self.client_checkboxes.remove(client_checkbox)

            for client_checkbox in self.client_checkboxes:
                client_process_id: int = client_checkbox.property("client").process_id  # process id that is stored

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
                    client_frame: QGroupBox = client_frame_info["frame"]
                    self.clients_tab_layout.removeWidget(client_frame)
                    client_frame.deleteLater()

            # Add new hooked clients
            for client in self.hooked_clients:
                if client.process_id not in self.client_frames:
                    client_frame: QGroupBox = QGroupBox(client.title)
                    client_frame_layout: QVBoxLayout = QVBoxLayout()

                    level_label: QLabel = QLabel(f"Level: {await client.stats.reference_level()}")

                    health_label: QLabel = QLabel(
                        f"Health: {await client.stats.current_hitpoints()}/{await client.stats.max_hitpoints()}"
                    )

                    mana_label: QLabel = QLabel(
                        f"Mana: {await client.stats.current_mana()}/{await client.stats.max_mana()}"
                    )

                    energy_label: QLabel = QLabel(
                        f"Energy: {await client.current_energy()}/{await client.stats.energy_max() + await client.stats.bonus_energy()}"
                    )

                    position_label: QLabel = QLabel(f"Position: {await client.body.position()}")
                    yaw_label: QLabel = QLabel(f"Yaw: {await client.body.yaw()}")

                    client_frame_layout.addWidget(level_label)
                    client_frame_layout.addWidget(health_label)
                    client_frame_layout.addWidget(mana_label)
                    client_frame_layout.addWidget(energy_label)
                    client_frame_layout.addWidget(position_label)
                    client_frame_layout.addWidget(yaw_label)

                    self.client_frames[client.process_id] = {
                        "frame": client_frame,
                        "labels": {
                            "level": level_label,
                            "health": health_label,
                            "mana": mana_label,
                            "energy": energy_label,
                            "position": position_label,
                            "yaw": yaw_label,
                        },
                    }

                    client_frame.setLayout(client_frame_layout)
                    self.clients_tab_layout.addWidget(client_frame, alignment=Qt.AlignmentFlag.AlignTop)

                else:
                    client_labels: dict[str, QLabel] = self.client_frames[client.process_id]["labels"]
                    client_labels["level"].setText(f"Level: {await client.stats.reference_level()}")

                    client_labels["health"].setText(
                        f"Health: {await client.stats.current_hitpoints()}/{await client.stats.max_hitpoints()}"
                    )

                    client_labels["mana"].setText(
                        f"Mana: {await client.stats.current_mana()}/{await client.stats.max_mana()}"
                    )

                    client_labels["energy"].setText(
                        f"Energy: {await client.current_energy()}/{await client.stats.energy_max() + await client.stats.bonus_energy()}"
                    )

                    client_labels["position"].setText(f"Position: {await client.body.position()}")
                    client_labels["yaw"].setText(f"Yaw: {await client.body.yaw()}")

            await asyncio.sleep(1)


class KeysTab(QWidget):
    def __init__(self, utils: Utils, hooked_clients: list[Client]) -> None:
        super().__init__()
        self.utils: Utils = utils
        self.hooked_clients: list[Client] = hooked_clients

        # ----- Creating Layout ----- #
        self.keys_group_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.keys_group_layout)
        # --------------------------- #

        # ----- General Group ----- #
        general_group: QGroupBox = QGroupBox("General")
        general_group_layout: QHBoxLayout = QHBoxLayout()

        first_floor_button = WrapButton("1st Floor Teleport")
        first_floor_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        first_floor_button.clicked.connect(lambda: asyncio.create_task(self.first_floor_teleport()))

        second_floor_button = WrapButton("2nd Floor Teleport")
        second_floor_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        second_floor_button.clicked.connect(lambda: asyncio.create_task(self.second_floor_teleport()))

        freecam_teleport_button = WrapButton("Freecam Teleport")
        freecam_teleport_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        freecam_teleport_button.clicked.connect(lambda: asyncio.create_task(self.handle_freecam_teleport()))

        general_group_layout.addWidget(first_floor_button)
        general_group_layout.addWidget(second_floor_button)
        general_group_layout.addWidget(freecam_teleport_button)
        general_group.setLayout(general_group_layout)
        self.keys_group_layout.addWidget(general_group, stretch=1)
        # ------------------------- #

        # ----- Door Key Group ----- #
        door_key_group: QGroupBox = QGroupBox("Door Key")
        door_key_group_layout: QHBoxLayout = QHBoxLayout()

        key_freecam_teleport_button = WrapButton("Key Freecam Teleport")
        key_freecam_teleport_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        key_freecam_teleport_button.clicked.connect(lambda: asyncio.create_task(self.key_freecam_teleport()))

        door_key_group_layout.addWidget(key_freecam_teleport_button)
        door_key_group.setLayout(door_key_group_layout)
        self.keys_group_layout.addWidget(door_key_group, stretch=1)
        # -------------------------- #

        # ----- Doors Group ----- #
        doors_group: QGroupBox = QGroupBox("Doors")
        doors_group_layout: QVBoxLayout = QVBoxLayout()
        doors_grid: QGridLayout = QGridLayout()

        doom_oni_button = WrapButton("Doom Oni Door\nTeleport")
        doom_oni_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        doom_oni_button.clicked.connect(lambda: asyncio.create_task(self.doom_oni_door_teleport()))

        turmoil_oni_button = WrapButton("Turmoil Oni Door\nTeleport")
        turmoil_oni_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        turmoil_oni_button.clicked.connect(lambda: asyncio.create_task(self.turmoil_oni_door_teleport()))

        primal_oni_button = WrapButton("Primal Oni Door\nTeleport")
        primal_oni_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        primal_oni_button.clicked.connect(lambda: asyncio.create_task(self.primal_oni_door_teleport()))

        everwinter_oni_button = WrapButton("Everwinter Oni Door\nTeleport")
        everwinter_oni_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        everwinter_oni_button.clicked.connect(lambda: asyncio.create_task(self.everwinter_oni_door_teleport()))

        trickster_oni_button = WrapButton("Trickster Oni Door\nTeleport")
        trickster_oni_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        trickster_oni_button.clicked.connect(lambda: asyncio.create_task(self.trickster_oni_door_teleport()))

        infernal_oni_button = WrapButton("Infernal Oni Door\nTeleport")
        infernal_oni_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        infernal_oni_button.clicked.connect(lambda: asyncio.create_task(self.infernal_oni_door_teleport()))

        doors_grid.addWidget(doom_oni_button, 0, 0)
        doors_grid.addWidget(turmoil_oni_button, 0, 1)
        doors_grid.addWidget(primal_oni_button, 0, 2)
        doors_grid.addWidget(everwinter_oni_button, 1, 0)
        doors_grid.addWidget(trickster_oni_button, 1, 1)
        doors_grid.addWidget(infernal_oni_button, 1, 2)

        doors_group_layout.addLayout(doors_grid)
        doors_group.setLayout(doors_group_layout)
        self.keys_group_layout.addWidget(doors_group, stretch=2)
        # ----------------------- #

    async def first_floor_teleport(self) -> None:
        print("[TELEPORT] 1st Floor pressed")
        await self.utils.handle_basic_teleport(52550.0, 300.0, -10625.965)

    async def second_floor_teleport(self) -> None:
        print("[TELEPORT] 2nd Floor pressed")
        await self.utils.handle_basic_teleport(-55400.0, 300.0, -5123.629)

    async def handle_freecam_teleport(self) -> None:
        print("[FREECAM] Freecam Teleport pressed")

        if not self.utils.freecam_task:
            print("[FREECAM] Freecam is not active")

        if self.utils.freecam_task:
            self.utils.freecam_task.cancel()
            camera_pos: XYZ | None = await self.utils.freecam_task
            self.utils.freecam_task = None

            if camera_pos is not None:
                await self.utils.freecam_teleport(camera_pos)

    async def key_freecam_teleport(self) -> None:
        print("[FREECAM] Key Freecam Teleport pressed")
        await self.utils.entity_freecam_teleport("Raid_MS_Door_Key_01")

    async def doom_oni_door_teleport(self) -> None:
        print("[TELEPORT] Doom Oni Door pressed")
        await self.utils.handle_basic_teleport(49750.0, -850.0, -10625.967)

    async def turmoil_oni_door_teleport(self) -> None:
        print("[TELEPORT] Turmoil Oni Door pressed")
        await self.utils.handle_basic_teleport(52600.0, 750.0, -10625.967)

    async def primal_oni_door_teleport(self) -> None:
        print("[TELEPORT] Primal Oni Door pressed")
        await self.utils.handle_basic_teleport(55500.0, -750.0, -10625.966)

    async def everwinter_oni_door_teleport(self) -> None:
        print("[TELEPORT] Everwinter Oni Door pressed")
        await self.utils.handle_basic_teleport(49750.0, -4325.0, -10625.965)

    async def trickster_oni_door_teleport(self) -> None:
        print("[TELEPORT] Trickster Oni Door pressed")
        await self.utils.handle_basic_teleport(52600.0, -5950.0, -10625.967)

    async def infernal_oni_door_teleport(self) -> None:
        print("[TELEPORT] Infernal Oni Door pressed")
        await self.utils.handle_basic_teleport(55500.0, -4250.0, -10625.966)


class SeedsTab(QWidget):
    def __init__(self, utils: Utils, hooked_clients: list[Client]) -> None:
        super().__init__()
        self.utils: Utils = utils
        self.hooked_clients: list[Client] = hooked_clients

        # ----- Creating Layout ----- #
        self.seeds_group_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.seeds_group_layout)
        # --------------------------- #

        # ----- General Group ----- #
        general_group: QGroupBox = QGroupBox("General")
        general_group_layout: QHBoxLayout = QHBoxLayout()

        first_floor_button = WrapButton("1st Floor Teleport")
        first_floor_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        first_floor_button.clicked.connect(lambda: asyncio.create_task(self.first_floor_teleport()))

        second_floor_button = WrapButton("2nd Floor Teleport")
        second_floor_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        second_floor_button.clicked.connect(lambda: asyncio.create_task(self.second_floor_teleport()))

        freecam_teleport_button = WrapButton("Freecam Teleport")
        freecam_teleport_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        freecam_teleport_button.clicked.connect(lambda: asyncio.create_task(self.handle_freecam_teleport()))

        general_group_layout.addWidget(first_floor_button)
        general_group_layout.addWidget(second_floor_button)
        general_group_layout.addWidget(freecam_teleport_button)
        general_group.setLayout(general_group_layout)
        self.seeds_group_layout.addWidget(general_group, stretch=1)
        # ------------------------- #

        # ----- Seeds Group ----- #
        seeds_group: QGroupBox = QGroupBox("Seeds")
        seeds_group_layout: QVBoxLayout = QVBoxLayout()
        seeds_grid: QGridLayout = QGridLayout()

        doom_seed_button = WrapButton("Doom Seed\nFreecam Teleport")
        doom_seed_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        doom_seed_button.clicked.connect(lambda: asyncio.create_task(self.doom_seed_freecam_teleport()))

        turmoil_seed_button = WrapButton("Turmoil Seed\nFreecam Teleport")
        turmoil_seed_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        turmoil_seed_button.clicked.connect(lambda: asyncio.create_task(self.turmoil_seed_freecam_teleport()))

        primal_seed_button = WrapButton("Primal Seed\nFreecam Teleport")
        primal_seed_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        primal_seed_button.clicked.connect(lambda: asyncio.create_task(self.primal_seed_freecam_teleport()))

        everwinter_seed_button = WrapButton("Everwinter Seed\nFreecam Teleport")
        everwinter_seed_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        everwinter_seed_button.clicked.connect(lambda: asyncio.create_task(self.everwinter_seed_freecam_teleport()))

        trickster_seed_button = WrapButton("Trickster Seed\nFreecam Teleport")
        trickster_seed_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        trickster_seed_button.clicked.connect(lambda: asyncio.create_task(self.trickster_seed_freecam_teleport()))

        infernal_seed_button = WrapButton("Infernal Seed\nFreecam Teleport")
        infernal_seed_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        infernal_seed_button.clicked.connect(lambda: asyncio.create_task(self.infernal_seed_freecam_teleport()))

        seeds_grid.addWidget(doom_seed_button, 0, 0)
        seeds_grid.addWidget(turmoil_seed_button, 0, 1)
        seeds_grid.addWidget(primal_seed_button, 0, 2)
        seeds_grid.addWidget(everwinter_seed_button, 1, 0)
        seeds_grid.addWidget(trickster_seed_button, 1, 1)
        seeds_grid.addWidget(infernal_seed_button, 1, 2)

        seeds_group_layout.addLayout(seeds_grid)
        seeds_group.setLayout(seeds_group_layout)
        self.seeds_group_layout.addWidget(seeds_group, stretch=2)
        # ----------------------- #

        # ----- Planters and Dryads Group ----- #
        planters_dryads_group: QGroupBox = QGroupBox("Planters and Dryads")
        planters_dryads_group_layout: QVBoxLayout = QVBoxLayout()
        planters_dryads_grid: QGridLayout = QGridLayout()

        doom_dryad_button = WrapButton("Doom Dryad\nTeleport")
        doom_dryad_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        doom_dryad_button.clicked.connect(lambda: asyncio.create_task(self.doom_dryad_teleport()))

        turmoil_dryad_button = WrapButton("Turmoil Dryad\nTeleport")
        turmoil_dryad_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        turmoil_dryad_button.clicked.connect(lambda: asyncio.create_task(self.turmoil_dryad_teleport()))

        primal_dryad_button = WrapButton("Primal Dryad\nTeleport")
        primal_dryad_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        primal_dryad_button.clicked.connect(lambda: asyncio.create_task(self.primal_dryad_teleport()))

        everwinter_dryad_button = WrapButton("Everwinter Dryad\nTeleport")
        everwinter_dryad_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        everwinter_dryad_button.clicked.connect(lambda: asyncio.create_task(self.everwinter_dryad_teleport()))

        trickster_dryad_button = WrapButton("Trickster Dryad\nTeleport")
        trickster_dryad_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        trickster_dryad_button.clicked.connect(lambda: asyncio.create_task(self.trickster_dryad_teleport()))

        infernal_dryad_button = WrapButton("Infernal Dryad\nTeleport")
        infernal_dryad_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        infernal_dryad_button.clicked.connect(lambda: asyncio.create_task(self.infernal_dryad_teleport()))

        planters_dryads_grid.addWidget(doom_dryad_button, 0, 0)
        planters_dryads_grid.addWidget(turmoil_dryad_button, 0, 1)
        planters_dryads_grid.addWidget(primal_dryad_button, 0, 2)
        planters_dryads_grid.addWidget(everwinter_dryad_button, 1, 0)
        planters_dryads_grid.addWidget(trickster_dryad_button, 1, 1)
        planters_dryads_grid.addWidget(infernal_dryad_button, 1, 2)

        planters_dryads_group_layout.addLayout(planters_dryads_grid)
        planters_dryads_group.setLayout(planters_dryads_group_layout)
        self.seeds_group_layout.addWidget(planters_dryads_group, stretch=2)
        # ------------------------------------- #

        # ----- Braziers Group ----- #
        braziers_group: QGroupBox = QGroupBox("Braziers")
        braziers_group_layout: QHBoxLayout = QHBoxLayout()

        giver_time_torch_button = WrapButton("Giver of the Time Torch Teleport")
        giver_time_torch_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        giver_time_torch_button.clicked.connect(lambda: asyncio.create_task(self.giver_time_torch_teleport()))

        swifty_shop_button = WrapButton("Swifty's Swift Shop Teleport")
        swifty_shop_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        swifty_shop_button.clicked.connect(lambda: asyncio.create_task(self.swifty_shop_teleport()))

        braziers_group_layout.addWidget(giver_time_torch_button)
        braziers_group_layout.addWidget(swifty_shop_button)
        braziers_group.setLayout(braziers_group_layout)
        self.seeds_group_layout.addWidget(braziers_group, stretch=1)
        # -------------------------- #

    async def first_floor_teleport(self) -> None:
        print("[TELEPORT] 1st Floor pressed")
        await self.utils.handle_basic_teleport(52550.0, 300.0, -10625.965)

    async def second_floor_teleport(self) -> None:
        print("[TELEPORT] 2nd Floor pressed")
        await self.utils.handle_basic_teleport(-55400.0, 300.0, -5123.629)

    async def handle_freecam_teleport(self) -> None:
        print("[FREECAM] Freecam Teleport pressed")

        if not self.utils.freecam_task:
            print("[FREECAM] Freecam is not active")

        if self.utils.freecam_task:
            self.utils.freecam_task.cancel()
            camera_pos: XYZ | None = await self.utils.freecam_task
            self.utils.freecam_task = None

            if camera_pos is not None:
                await self.utils.freecam_teleport(camera_pos)

    async def doom_seed_freecam_teleport(self) -> None:
        print("[FREECAM] Doom Seed Freecam Teleport pressed")
        await self.utils.entity_freecam_teleport("GR_MS_Plant_06_Seed")

    async def turmoil_seed_freecam_teleport(self) -> None:
        print("[FREECAM] Turmoil Seed Freecam Teleport pressed")
        await self.utils.entity_freecam_teleport("GR_MS_Plant_03_Seed")

    async def primal_seed_freecam_teleport(self) -> None:
        print("[FREECAM] Primal Seed Freecam Teleport pressed")
        await self.utils.entity_freecam_teleport("GR_MS_Plant_05_Seed")

    async def everwinter_seed_freecam_teleport(self) -> None:
        print("[FREECAM] Everwinter Seed Freecam Teleport pressed")
        await self.utils.entity_freecam_teleport("GR_MS_Plant_02_Seed")

    async def trickster_seed_freecam_teleport(self) -> None:
        print("[FREECAM] Trickster Seed Freecam Teleport pressed")
        await self.utils.entity_freecam_teleport("GR_MS_Plant_04_Seed")

    async def infernal_seed_freecam_teleport(self) -> None:
        print("[FREECAM] Infernal Seed Freecam Teleport pressed")
        await self.utils.entity_freecam_teleport("GR_MS_Plant_01_Seed")

    async def doom_dryad_teleport(self) -> None:
        print("[TELEPORT] Doom Dryad pressed")
        await self.utils.handle_basic_teleport(-59250.0, -400.0, -5122.860)

    async def turmoil_dryad_teleport(self) -> None:
        print("[TELEPORT] Turmoil Dryad pressed")
        await self.utils.handle_basic_teleport(-55500.0, 1850.0, -5122.856)

    async def primal_dryad_teleport(self) -> None:
        print("[TELEPORT] Primal Dryad pressed")
        await self.utils.handle_basic_teleport(-51500.0, -350.0, -5122.854)

    async def everwinter_dryad_teleport(self) -> None:
        print("[TELEPORT] Everwinter Dryad pressed")
        await self.utils.handle_basic_teleport(-59250.0, -4750.0, -5122.870)

    async def trickster_dryad_teleport(self) -> None:
        print("[TELEPORT] Trickster Dryad pressed")
        await self.utils.handle_basic_teleport(-55400.0, -7000.0, -5122.858)

    async def infernal_dryad_teleport(self) -> None:
        print("[TELEPORT] Infernal Dryad pressed")
        await self.utils.handle_basic_teleport(-51750.0, -4750.0, -5122.860)

    async def giver_time_torch_teleport(self) -> None:
        print("[TELEPORT] Giver of the Time Torch pressed")
        await self.utils.handle_basic_teleport(-54850.0, -4210.0, -5123.630)

    async def swifty_shop_teleport(self) -> None:
        print("[TELEPORT] Swifty's Swift Shop pressed")
        await self.utils.handle_basic_teleport(-55450.0, -625.0, -5123.629)


class Phase1Tab(QWidget):
    def __init__(self, utils: Utils, hooked_clients: list[Client]) -> None:
        super().__init__()
        self.utils: Utils = utils
        self.hooked_clients: list[Client] = hooked_clients

        # ----- Creating Layout ----- #
        self.phase1_group_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.phase1_group_layout)
        # --------------------------- #

        # ----- General Group ----- #
        general_group: QGroupBox = QGroupBox("General")
        general_group_layout: QVBoxLayout = QVBoxLayout()
        general_grid: QGridLayout = QGridLayout()

        wisp_teleport_button = WrapButton("Wisp Teleport")
        wisp_teleport_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        wisp_teleport_button.clicked.connect(lambda: asyncio.create_task(self.wisp_teleport()))

        north_intersection_button = WrapButton("North Intersection Teleport")
        north_intersection_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        north_intersection_button.clicked.connect(lambda: asyncio.create_task(self.north_intersection_teleport()))

        east_intersection_button = WrapButton("East Intersection Teleport")
        east_intersection_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        east_intersection_button.clicked.connect(lambda: asyncio.create_task(self.east_intersection_teleport()))

        south_intersection_button = WrapButton("South Intersection Teleport")
        south_intersection_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        south_intersection_button.clicked.connect(lambda: asyncio.create_task(self.south_intersection_teleport()))

        west_intersection_button = WrapButton("West Intersection Teleport")
        west_intersection_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        west_intersection_button.clicked.connect(lambda: asyncio.create_task(self.west_intersection_teleport()))

        general_grid.addWidget(wisp_teleport_button, 0, 0, 1, 4)
        general_grid.addWidget(north_intersection_button, 1, 0)
        general_grid.addWidget(east_intersection_button, 1, 1)
        general_grid.addWidget(south_intersection_button, 1, 2)
        general_grid.addWidget(west_intersection_button, 1, 3)

        general_group_layout.addLayout(general_grid)
        general_group.setLayout(general_group_layout)
        self.phase1_group_layout.addWidget(general_group, stretch=2)
        # ------------------------- #

        # ----- Shrines Group ----- #
        shrines_group: QGroupBox = QGroupBox("Shrines")
        shrines_group_layout: QVBoxLayout = QVBoxLayout()
        shrines_grid: QGridLayout = QGridLayout()

        death_shrine_button = WrapButton("Death Shrine (NW)\nTeleport")
        death_shrine_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        death_shrine_button.clicked.connect(lambda: asyncio.create_task(self.death_shrine_teleport()))

        storm_shrine_button = WrapButton("Storm Shrine (N)\nTeleport")
        storm_shrine_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        storm_shrine_button.clicked.connect(lambda: asyncio.create_task(self.storm_shrine_teleport()))

        life_shrine_button = WrapButton("Life Shrine (NE)\nTeleport")
        life_shrine_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        life_shrine_button.clicked.connect(lambda: asyncio.create_task(self.life_shrine_teleport()))

        ice_shrine_button = WrapButton("Ice Shrine (SW)\nTeleport")
        ice_shrine_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        ice_shrine_button.clicked.connect(lambda: asyncio.create_task(self.ice_shrine_teleport()))

        myth_shrine_button = WrapButton("Myth Shrine (S)\nTeleport")
        myth_shrine_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        myth_shrine_button.clicked.connect(lambda: asyncio.create_task(self.myth_shrine_teleport()))

        fire_shrine_button = WrapButton("Fire Shrine (SE)\nTeleport")
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
        self.phase1_group_layout.addWidget(shrines_group, stretch=2)
        # ------------------------- #

        # ----- Essence Forges Group ----- #
        essence_forge_group: QGroupBox = QGroupBox("Essence Forges")
        essence_forge_group_layout: QHBoxLayout = QHBoxLayout()

        essence_forge_north_button = WrapButton("North Essence Forge Teleport")
        essence_forge_north_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        essence_forge_north_button.clicked.connect(lambda: asyncio.create_task(self.essence_forge_north_teleport()))

        essence_forge_east_button = WrapButton("East Essence Forge Teleport")
        essence_forge_east_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        essence_forge_east_button.clicked.connect(lambda: asyncio.create_task(self.essence_forge_east_teleport()))

        essence_forge_south_button = WrapButton("South Essence Forge Teleport")
        essence_forge_south_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        essence_forge_south_button.clicked.connect(lambda: asyncio.create_task(self.essence_forge_south_teleport()))

        essence_forge_west_button = WrapButton("West Essence Forge Teleport")
        essence_forge_west_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        essence_forge_west_button.clicked.connect(lambda: asyncio.create_task(self.essence_forge_west_teleport()))

        essence_forge_group_layout.addWidget(essence_forge_north_button)
        essence_forge_group_layout.addWidget(essence_forge_east_button)
        essence_forge_group_layout.addWidget(essence_forge_south_button)
        essence_forge_group_layout.addWidget(essence_forge_west_button)
        essence_forge_group.setLayout(essence_forge_group_layout)
        self.phase1_group_layout.addWidget(essence_forge_group, stretch=1)
        # -------------------------------- #

    async def wisp_teleport(self) -> None:
        print("[TELEPORT] Wisp Teleport pressed")
        await self.utils.wisp_teleport()

    async def north_intersection_teleport(self) -> None:
        print("[TELEPORT] North Intersection pressed")
        await self.utils.handle_basic_teleport(0.0, 5500.0, 210.490)

    async def east_intersection_teleport(self) -> None:
        print("[TELEPORT] East Intersection pressed")
        await self.utils.handle_basic_teleport(7000.0, -2350.0, 211.516)

    async def south_intersection_teleport(self) -> None:
        print("[TELEPORT] South Intersection pressed")
        await self.utils.handle_basic_teleport(-1250.0, -10000.0, 211.516)

    async def west_intersection_teleport(self) -> None:
        print("[TELEPORT] West Intersection pressed")
        await self.utils.handle_basic_teleport(-8000.0, -2300.0, 210.488)

    async def death_shrine_teleport(self) -> None:
        print("[TELEPORT] Death Shrine (North West) pressed")
        await self.utils.handle_basic_teleport(-11000.0, 2500.0, 229.305)

    async def storm_shrine_teleport(self) -> None:
        print("[TELEPORT] Storm Shrine (North) pressed")
        await self.utils.handle_basic_teleport(2000.0, 11200.0, 211.516)

    async def life_shrine_teleport(self) -> None:
        print("[TELEPORT] Life Shrine (North East) pressed")
        await self.utils.handle_basic_teleport(10000.0, 3500.0, 231.175)

    async def ice_shrine_teleport(self) -> None:
        print("[TELEPORT] Ice Shrine (South West) pressed")
        await self.utils.handle_basic_teleport(-11000.0, -8000.0, 224.645)

    async def myth_shrine_teleport(self) -> None:
        print("[TELEPORT] Myth Shrine (South) pressed")
        await self.utils.handle_basic_teleport(-3000.0, -15900.0, 231.804)

    async def fire_shrine_teleport(self) -> None:
        print("[TELEPORT] Fire Shrine (South East) pressed")
        await self.utils.handle_basic_teleport(10000.0, -7000.0, 230.445)

    async def essence_forge_north_teleport(self) -> None:
        print("[TELEPORT] Essence Forge North pressed")
        await self.utils.handle_basic_teleport(0.0, 200.0, 204.203)

    async def essence_forge_east_teleport(self) -> None:
        print("[TELEPORT] Essence Forge East pressed")
        await self.utils.handle_basic_teleport(2300.0, -2300.0, 213.011)

    async def essence_forge_south_teleport(self) -> None:
        print("[TELEPORT] Essence Forge South pressed")
        await self.utils.handle_basic_teleport(-1350.0, -5000.0, 207.070)

    async def essence_forge_west_teleport(self) -> None:
        print("[TELEPORT] Essence Forge West pressed")
        await self.utils.handle_basic_teleport(-3600.0, -2300.0, 211.996)


class Phase2Tab(QWidget):
    def __init__(self, utils: Utils, hooked_clients: list[Client]) -> None:
        super().__init__()
        self.utils: Utils = utils
        self.hooked_clients: list[Client] = hooked_clients

        # ----- Creating Layout ----- #
        self.phase2_group_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.phase2_group_layout)
        # --------------------------- #

        # ----- General Group ----- #
        general_group: QGroupBox = QGroupBox("General")
        general_group_layout: QVBoxLayout = QVBoxLayout()
        general_grid: QGridLayout = QGridLayout()

        wisp_teleport_button = WrapButton("Wisp Teleport")
        wisp_teleport_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        wisp_teleport_button.clicked.connect(lambda: asyncio.create_task(self.wisp_teleport()))

        north_pagoda_button = WrapButton("North Pagoda Teleport")
        north_pagoda_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        north_pagoda_button.clicked.connect(lambda: asyncio.create_task(self.north_pagoda_teleport()))

        east_pagoda_button = WrapButton("East Pagoda Teleport")
        east_pagoda_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        east_pagoda_button.clicked.connect(lambda: asyncio.create_task(self.east_pagoda_teleport()))

        south_pagoda_button = WrapButton("South Pagoda Teleport")
        south_pagoda_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        south_pagoda_button.clicked.connect(lambda: asyncio.create_task(self.south_pagoda_teleport()))

        west_pagoda_button = WrapButton("West Pagoda Teleport")
        west_pagoda_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        west_pagoda_button.clicked.connect(lambda: asyncio.create_task(self.west_pagoda_teleport()))

        general_grid.addWidget(wisp_teleport_button, 0, 0, 1, 4)
        general_grid.addWidget(north_pagoda_button, 1, 0)
        general_grid.addWidget(east_pagoda_button, 1, 1)
        general_grid.addWidget(south_pagoda_button, 1, 2)
        general_grid.addWidget(west_pagoda_button, 1, 3)

        general_group_layout.addLayout(general_grid)
        general_group.setLayout(general_group_layout)
        self.phase2_group_layout.addWidget(general_group, stretch=2)
        # ------------------------- #

        # ----- Time Torch Group ----- #
        time_torch_group: QGroupBox = QGroupBox("Time Torch")
        time_torch_group_layout: QHBoxLayout = QHBoxLayout()

        freecam_teleport_button = WrapButton("Freecam Teleport")
        freecam_teleport_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        freecam_teleport_button.clicked.connect(lambda: asyncio.create_task(self.handle_freecam_teleport()))

        time_torch_teleport_button = WrapButton("Time Torch Freecam Teleport")
        time_torch_teleport_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        time_torch_teleport_button.clicked.connect(lambda: asyncio.create_task(self.time_torch_teleport()))

        time_torch_group_layout.addWidget(time_torch_teleport_button)
        time_torch_group_layout.addWidget(freecam_teleport_button)
        time_torch_group.setLayout(time_torch_group_layout)
        self.phase2_group_layout.addWidget(time_torch_group, stretch=1)
        # ---------------------------- #

        # ----- Urnings Group ----- #
        urnings_group: QGroupBox = QGroupBox("Urnings")
        urnings_group_layout: QHBoxLayout = QHBoxLayout()

        elemental_urning_button = WrapButton("Elemental Urning Teleport")
        elemental_urning_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        elemental_urning_button.clicked.connect(lambda: asyncio.create_task(self.elemental_urning_teleport()))

        spirit_urning_button = WrapButton("Spirit Urning Teleport")
        spirit_urning_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        spirit_urning_button.clicked.connect(lambda: asyncio.create_task(self.spirit_urning_teleport()))

        urnings_group_layout.addWidget(elemental_urning_button)
        urnings_group_layout.addWidget(spirit_urning_button)
        urnings_group.setLayout(urnings_group_layout)
        self.phase2_group_layout.addWidget(urnings_group, stretch=1)
        # ------------------------- #

    async def wisp_teleport(self) -> None:
        print("[TELEPORT] Wisp Teleport pressed")
        await self.utils.wisp_teleport()

    async def north_pagoda_teleport(self) -> None:
        print("[TELEPORT] North Pagoda pressed")
        await self.utils.handle_basic_teleport(0.0, 200.0, 204.203)

    async def east_pagoda_teleport(self) -> None:
        print("[TELEPORT] East Pagoda pressed")
        await self.utils.handle_basic_teleport(2300.0, -2300.0, 213.011)

    async def south_pagoda_teleport(self) -> None:
        print("[TELEPORT] South Pagoda pressed")
        await self.utils.handle_basic_teleport(-1350.0, -5000.0, 207.070)

    async def west_pagoda_teleport(self) -> None:
        print("[TELEPORT] West Pagoda pressed")
        await self.utils.handle_basic_teleport(-3600.0, -2300.0, 211.996)

    async def time_torch_teleport(self) -> None:
        print("[FREECAM] Time Torch Freecam Teleport pressed")
        await self.utils.entity_freecam_teleport("Raid_MS_TimeTorch")

    async def handle_freecam_teleport(self) -> None:
        print("[FREECAM] Freecam Teleport pressed")

        if not self.utils.freecam_task:
            print("[FREECAM] Freecam is not active")

        if self.utils.freecam_task:
            self.utils.freecam_task.cancel()
            camera_pos: XYZ | None = await self.utils.freecam_task
            self.utils.freecam_task = None

            if camera_pos is not None:
                await self.utils.freecam_teleport(camera_pos)

    async def elemental_urning_teleport(self) -> None:
        print("[TELEPORT] Elemental Urning pressed")
        await self.utils.handle_basic_teleport(1700.0, -4700.0, 204.203)

    async def spirit_urning_teleport(self) -> None:
        print("[TELEPORT] Spirit Urning pressed")
        await self.utils.handle_basic_teleport(-2300.0, -200.0, 204.203)


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
        drum_teleport_button = WrapButton("Drum Teleport")
        drum_teleport_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        drum_teleport_button.clicked.connect(lambda: asyncio.create_task(self.drum_teleport()))

        self.drums_tab_layout.addWidget(drum_teleport_button)
        # -------------------------------- #

        # ----- Auto Drums Button ----- #
        auto_drums_button = WrapButton("Auto Drums")
        auto_drums_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        auto_drums_button.clicked.connect(lambda: asyncio.create_task(self.auto_drums()))
        self.drums_tab_layout.addWidget(auto_drums_button)
        # ---------------------------- #

    async def drum_teleport(self) -> None:
        print("[DRUMS] Drum Teleport pressed")
        await self.utils.raid_drum_teleport()

    async def auto_drums(self) -> None:
        print("[DRUMS] Auto Drums pressed")

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
        self.experimental_group_layout.addWidget(self.experimental_group, stretch=1)
        # --------------------------------------- #

        # ----- Toggle Minimap Button ----- #
        toggle_minimap_button = WrapButton("Toggle Minimap")

        toggle_minimap_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        toggle_minimap_button.clicked.connect(lambda: asyncio.create_task(self.toggle_minimap()))

        self.experimental_tab_layout.addWidget(toggle_minimap_button)
        # --------------------------------- #

        # ----- Mobs Group ----- #
        mobs_group: QGroupBox = QGroupBox("Mobs")
        mobs_group_layout: QVBoxLayout = QVBoxLayout()
        mobs_grid: QGridLayout = QGridLayout()

        doom_button = WrapButton("Doom Yaoguai (Death)\nTeleport")
        doom_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        doom_button.clicked.connect(lambda: asyncio.create_task(self.doom_yaoguai_teleport()))

        turmoil_button = WrapButton("Turmoil Yaoguai (Storm)\nTeleport")
        turmoil_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        turmoil_button.clicked.connect(lambda: asyncio.create_task(self.turmoil_yaoguai_teleport()))

        primeval_button = WrapButton("Primeval Yaoguai (Life)\nTeleport")
        primeval_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        primeval_button.clicked.connect(lambda: asyncio.create_task(self.primeval_yaoguai_teleport()))

        everwinter_button = WrapButton("Everwinter Yaoguai (Ice)\nTeleport")
        everwinter_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        everwinter_button.clicked.connect(lambda: asyncio.create_task(self.everwinter_yaoguai_teleport()))

        trickster_button = WrapButton("Trickster Yaoguai (Myth)\nTeleport")
        trickster_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        trickster_button.clicked.connect(lambda: asyncio.create_task(self.trickster_yaoguai_teleport()))

        infernal_button = WrapButton("Infernal Yaoguai (Fire)\nTeleport")
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
        self.experimental_group_layout.addWidget(mobs_group, stretch=2)
        # --------------------- #

    async def toggle_minimap(self) -> None:
        print("[EXPERIMENTAL] Toggle Minimap pressed")
        for client in self.hooked_clients:
            await self.utils.toggle_minimap(client)

    async def doom_yaoguai_teleport(self) -> None:
        print("[TELEPORT] Doom Yaoguai (Death) pressed")
        await self.utils.mob_entity_teleport("GR_MS_Spider_BlackWidow_A_01_NC")

    async def turmoil_yaoguai_teleport(self) -> None:
        print("[TELEPORT] Turmoil Yaoguai (Storm) pressed")
        await self.utils.mob_entity_teleport("GR_MS_Dragon_Sky_A_01_NC")

    async def primeval_yaoguai_teleport(self) -> None:
        print("[TELEPORT] Primeval Yaoguai (Life) pressed")
        await self.utils.mob_entity_teleport("GR_MS_Treant_Base_A_01_NC")

    async def everwinter_yaoguai_teleport(self) -> None:
        print("[TELEPORT] Everwinter Yaoguai (Ice) pressed")
        await self.utils.mob_entity_teleport("GR_MS_Ghost_LostSoul_E_01_NC")

    async def trickster_yaoguai_teleport(self) -> None:
        print("[TELEPORT] Trickster Yaoguai (Myth) pressed")
        await self.utils.mob_entity_teleport("GR_MS_Colossus_Stone_A_01_NC")

    async def infernal_yaoguai_teleport(self) -> None:
        print("[TELEPORT] Infernal Yaoguai (Fire) pressed")
        await self.utils.mob_entity_teleport("GR_MS_Samoorai_Clay_A_01_NC")


class UtilityTab(QWidget):
    def __init__(self, utils: Utils, hooked_clients: list[Client]) -> None:
        super().__init__()
        self.utils: Utils = utils
        self.hooked_clients: list[Client] = hooked_clients

        self.auto_dialogue_tasks: dict[Client, asyncio.Task[None]] = {}
        self.speedhack_tasks: dict[Client, asyncio.Task[None]] = {}

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

        speedhack_button = WrapButton("Toggle Speedhack")
        speedhack_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
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
        auto_dialogue_button = WrapButton("Toggle Auto Dialogue")
        auto_dialogue_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        auto_dialogue_button.clicked.connect(lambda: asyncio.create_task(self.toggle_auto_dialogue()))
        self.utility_tab_layout.addWidget(auto_dialogue_button)
        # -------------------------------- #

        # ----- Freecam Button ----- #
        freecam_button = WrapButton("Toggle Freecam")
        freecam_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        freecam_button.clicked.connect(lambda: asyncio.create_task(self.toggle_freecam()))
        self.utility_tab_layout.addWidget(freecam_button)
        # -------------------------- #

        # ----- Freecam Teleport Button ----- #
        freecam_teleport_button = WrapButton("Freecam Teleport")
        freecam_teleport_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        freecam_teleport_button.clicked.connect(lambda: asyncio.create_task(self.handle_freecam_teleport()))
        self.utility_tab_layout.addWidget(freecam_teleport_button)
        # ---------------------------------- #

        # ----- XYZ Sync Button ----- #
        xyz_sync_button = WrapButton("XYZ Sync")
        xyz_sync_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        xyz_sync_button.clicked.connect(lambda: asyncio.create_task(self.handle_xyz_sync()))
        self.utility_tab_layout.addWidget(xyz_sync_button)
        # --------------------------- #

        # ----- Copy Position Button ----- #
        copy_position_button = WrapButton("Copy Position")
        copy_position_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        copy_position_button.clicked.connect(lambda: asyncio.create_task(self.handle_copy_position()))
        self.utility_tab_layout.addWidget(copy_position_button)
        # -------------------------------- #

    async def toggle_auto_dialogue(self) -> None:
        print("[UTILITY] Auto Dialogue pressed")

        if not self.auto_dialogue_tasks:
            for client in self.hooked_clients:
                self.auto_dialogue_tasks[client] = asyncio.create_task(self.utils.handle_auto_dialogue(client))

            return

        if self.auto_dialogue_tasks:
            for client, auto_dialogue_task in self.auto_dialogue_tasks.items():
                auto_dialogue_task.cancel()

            self.auto_dialogue_tasks = {}

    async def toggle_speedhack(self) -> None:
        print("[UTILITY] Speedhack pressed")

        if not self.speedhack_tasks:
            for client in self.hooked_clients:
                self.speedhack_tasks[client] = asyncio.create_task(
                    self.utils.handle_speedhack(client, self.speedhack_spinbox.value() * 100)
                )

            return

        if self.speedhack_tasks:
            for client, speedhack_task in self.speedhack_tasks.items():
                speedhack_task.cancel()

            self.speedhack_tasks = {}

    async def toggle_freecam(self) -> None:
        print("[UTILITY] Freecam pressed")

        if not self.utils.freecam_task:
            if self.hooked_clients:
                self.utils.freecam_task = asyncio.create_task(self.utils.handle_freecam())
                return

        if self.utils.freecam_task:
            self.utils.freecam_task.cancel()
            self.utils.freecam_task = None
            print("[TOGGLE] Freecam cancelled")

    async def handle_freecam_teleport(self) -> None:
        print("[FREECAM] Freecam Teleport pressed")

        if not self.utils.freecam_task:
            print("[FREECAM] Freecam is not active")

        if self.utils.freecam_task:
            self.utils.freecam_task.cancel()
            camera_pos: XYZ | None = await self.utils.freecam_task
            self.utils.freecam_task = None

            if camera_pos is not None:
                await self.utils.freecam_teleport(camera_pos)

    async def handle_xyz_sync(self) -> None:
        print("[UTILITY] XYZ Sync pressed")
        await self.utils.xyz_sync()

    async def handle_copy_position(self) -> None:
        print("[UTILITY] Copy Position pressed")
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
        default_theme_button_button = WrapButton("Default Theme")
        default_theme_button_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        default_theme_button_button.clicked.connect(self.enable_default_theme)
        self.main_themes_group_layout.addWidget(default_theme_button_button)
        # -------------------------------- #

        # ----- Custom Theme Button ----- #
        custom_theme_button_button = WrapButton("Custom Theme")
        custom_theme_button_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        custom_theme_button_button.clicked.connect(self.enable_custom_theme)
        self.main_themes_group_layout.addWidget(custom_theme_button_button)
        # ------------------------------- #

        # ----- Night Theme Button ----- #
        night_theme_button_button = WrapButton("Night Theme")
        night_theme_button_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        night_theme_button_button.clicked.connect(self.enable_night_theme)
        self.preset_themes_group_layout.addWidget(night_theme_button_button)
        # ------------------------------ #

        # ----- Celestia Theme Button ----- #
        celestia_theme_button_button = WrapButton("Celestia Theme")
        celestia_theme_button_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        celestia_theme_button_button.clicked.connect(self.enable_celestia_theme)
        self.preset_themes_group_layout.addWidget(celestia_theme_button_button)
        # --------------------------------- #

        # ----- Mooshu Theme Button ----- #
        mooshu_theme_button_button = WrapButton("Mooshu Theme")
        mooshu_theme_button_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        mooshu_theme_button_button.clicked.connect(self.enable_mooshu_theme)
        self.preset_themes_group_layout.addWidget(mooshu_theme_button_button)
        # ------------------------------ #

        self.main_themes_group.setLayout(self.main_themes_group_layout)
        self.preset_themes_group.setLayout(self.preset_themes_group_layout)

        self.themes_tab_layout.addWidget(self.main_themes_group)
        self.themes_tab_layout.addWidget(self.preset_themes_group)

    def enable_default_theme(self) -> None:
        print("[THEMES] Default theme enabled")

        if window := self.window():
            window.setStyleSheet(self.themes.default)

    def enable_custom_theme(self) -> None:
        print("[THEMES] Custom theme enabled")

        if window := self.window():
            window.setStyleSheet(self.themes.custom_theme)

    def enable_night_theme(self) -> None:
        print("[THEMES] Night theme enabled")

        if window := self.window():
            window.setStyleSheet(self.themes.night)

    def enable_celestia_theme(self) -> None:
        print("[THEMES] Celestia theme enabled")

        if window := self.window():
            window.setStyleSheet(self.themes.celestia)

    def enable_mooshu_theme(self) -> None:
        print("[THEMES] Mooshu theme enabled")

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

        self.keys_tab: KeysTab = KeysTab(self.utils, self.hooked_clients)
        self.seeds_tab: SeedsTab = SeedsTab(self.utils, self.hooked_clients)
        self.phase1_tab: Phase1Tab = Phase1Tab(self.utils, self.hooked_clients)
        self.phase2_tab: Phase2Tab = Phase2Tab(self.utils, self.hooked_clients)
        self.drums_tab: DrumsTab = DrumsTab(self.utils, self.hooked_clients)
        self.experimental_tab: ExperimentalTab = ExperimentalTab(self.utils, self.hooked_clients)
        self.utility_tab: UtilityTab = UtilityTab(self.utils, self.hooked_clients)
        self.themes_tab: ThemesTab = ThemesTab(self.themes)

        tabs.addTab(self.hooks_tab, "Hooks")

        if self.enable_clients_tab:
            tabs.addTab(self.clients_tab, "Clients")

        tabs.addTab(self.keys_tab, "Keys")
        tabs.addTab(self.seeds_tab, "Seeds")
        tabs.addTab(self.phase1_tab, "Phase 1")
        tabs.addTab(self.phase2_tab, "Phase 2")
        tabs.addTab(self.drums_tab, "Drums")
        tabs.addTab(self.experimental_tab, "Experimental")
        tabs.addTab(self.utility_tab, "Utility")
        tabs.addTab(self.themes_tab, "Themes")

        layout.addWidget(tabs)

        # Creating footer
        footers_layout: QHBoxLayout = QHBoxLayout()

        donation_link_label: QLabel = QLabel('<a href="https://www.buymeacoffee.com/lxghtend">Donate</a>')
        donation_link_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        credit_label: QLabel = QLabel(
            'Made by Lxghtend (<a href="https://github.com/Lxghtend">https://github.com/Lxghtend</a>)'
        )

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

        donate_button = WrapButton("Donate")
        donate_button.clicked.connect(self.open_donate)

        ok_button = WrapButton("Ok")
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
