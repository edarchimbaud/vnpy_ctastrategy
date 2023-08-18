from datetime import datetime
from time import sleep
from typing import TYPE_CHECKING, List, Optional
from copy import copy

from vnpy.trader.engine import MainEngine
from vnpy.trader.constant import OrderType
from vnpy.trader.object import ContractData, OrderRequest, SubscribeRequest, TickData
from vnpy.trader.object import Direction, Offset
from vnpy.trader.ui import QtWidgets
from vnpy.trader.converter import OffsetConverter, PositionHolding

from ..engine import CtaEngine, APP_NAME
from ..template import CtaTemplate

if TYPE_CHECKING:
    from .widget import CtaManager


class RolloverTool(QtWidgets.QDialog):
    """"""

    def __init__(self, cta_manager: "CtaManager") -> None:
        """"""
        super().__init__()

        self.cta_manager: "CtaManager" = cta_manager
        self.cta_engine: CtaEngine = cta_manager.cta_engine
        self.main_engine: MainEngine = cta_manager.main_engine

        self.init_ui()

    def init_ui(self) -> None:
        """"""
        self.setWindowTitle("Rollover Tool")

        old_symbols: list = []
        for vt_symbol, strategies in self.cta_engine.symbol_strategy_map.items():
            if strategies:
                old_symbols.append(vt_symbol)
        self.old_symbol_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.old_symbol_combo.addItems(old_symbols)

        self.new_symbol_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()

        self.payup_spin: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.payup_spin.setMinimum(5)

        self.max_volume_spin: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.max_volume_spin.setMinimum(1)
        self.max_volume_spin.setMaximum(10000)
        self.max_volume_spin.setValue(100)

        self.log_edit: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumWidth(500)

        button: QtWidgets.QPushButton = QtWidgets.QPushButton("Roll")
        button.clicked.connect(self.roll_all)
        button.setFixedHeight(button.sizeHint().height() * 2)

        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow("Old symbol", self.old_symbol_combo)
        form.addRow("New symbol", self.new_symbol_line)
        form.addRow("Pay up spin", self.payup_spin)
        form.addRow("Max volume spin", self.max_volume_spin)
        form.addRow(button)

        hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox.addLayout(form)
        hbox.addWidget(self.log_edit)
        self.setLayout(hbox)

    def write_log(self, text: str) -> None:
        """"""
        now: datetime = datetime.now()
        text: str = now.strftime("%H:%M:%S\t") + text
        self.log_edit.append(text)

    def subscribe(self, vt_symbol: str) -> None:
        """"""
        contract: Optional[ContractData] = self.main_engine.get_contract(vt_symbol)
        if not contract:
            return

        req: SubscribeRequest = SubscribeRequest(contract.symbol, contract.exchange)
        self.main_engine.subscribe(req, contract.gateway_name)

    def roll_all(self) -> None:
        """"""
        old_symbol: str = self.old_symbol_combo.currentText()

        new_symbol: str = self.new_symbol_line.text()
        self.subscribe(new_symbol)
        sleep(1)

        new_tick: Optional[TickData] = self.main_engine.get_tick(new_symbol)
        if not new_tick:
            self.write_log(f"Unable to get intraday data for target contract {new_symbol}, please subscribe to the ticker first")
            return

        payup: int = self.payup_spin.value()

        # Check all strategies inited (pos data loaded from disk json file) and not trading
        strategies: list = self.cta_engine.symbol_strategy_map[old_symbol]
        for strategy in strategies:
            if not strategy.inited:
                self.write_log(f"Strategy {strategy.strategy_name} has not yet been initialized, unable to execute position shift")
                return

            if strategy.trading:
                self.write_log(f"Strategy {strategy.strategy_name} is running and can't execute a position move")
                return

        # Roll position first
        self.roll_position(old_symbol, new_symbol, payup)

        # Then roll strategy
        for strategy in copy(strategies):
            self.roll_strategy(strategy, new_symbol)

        # Disable self
        self.setEnabled(False)

    def roll_position(self, old_symbol: str, new_symbol: str, payup: int) -> None:
        """"""
        contract: ContractData = self.main_engine.get_contract(old_symbol)
        converter: OffsetConverter = self.main_engine.get_converter(contract.gateway_name)
        holding: PositionHolding = converter.get_position_holding(old_symbol)

        # Roll long position
        if holding.long_pos:
            volume: float = holding.long_pos

            self.send_order(
                old_symbol,
                Direction.SHORT,
                Offset.CLOSE,
                payup,
                volume
            )

            self.send_order(
                new_symbol,
                Direction.LONG,
                Offset.OPEN,
                payup,
                volume
            )

        # Roll short postiion
        if holding.short_pos:
            volume: float = holding.short_pos

            self.send_order(
                old_symbol,
                Direction.LONG,
                Offset.CLOSE,
                payup,
                volume
            )

            self.send_order(
                new_symbol,
                Direction.SHORT,
                Offset.OPEN,
                payup,
                volume
            )

    def roll_strategy(self, strategy: CtaTemplate, vt_symbol: str) -> None:
        """"""
        if not strategy.inited:
            self.cta_engine._init_strategy(strategy.strategy_name)

        # Save data of old strategy
        pos = strategy.pos
        name: str = strategy.strategy_name
        parameters: dict = strategy.get_parameters()

        # Remove old strategy
        result: bool = self.cta_engine.remove_strategy(name)
        if result:
            self.cta_manager.remove_strategy(name)

        self.write_log(f"Remove old strategy {name}[{strategy.vt_symbol}]")

        # Add new strategy
        self.cta_engine.add_strategy(
            strategy.__class__.__name__,
            name,
            vt_symbol,
            parameters
        )
        self.write_log(f"Create strategy {name}[{vt_symbol}]")

        # Init new strategy
        self.cta_engine.init_strategy(name)
        self.write_log(f"Initialization strategy {name}[{vt_symbol}]")

        # Update pos to new strategy
        new_strategy: CtaTemplate = self.cta_engine.strategies[name]
        new_strategy.pos = pos
        new_strategy.sync_data()
        self.write_log(f"Update strategy position {name}[{vt_symbol}]")

    def send_order(
        self,
        vt_symbol: str,
        direction: Direction,
        offset: Offset,
        payup: int,
        volume: float,
    ) -> None:
        """
        Send a new order to server.
        """
        max_volume: int = self.max_volume_spin.value()

        contract: Optional[ContractData] = self.main_engine.get_contract(vt_symbol)
        tick: Optional[TickData] = self.main_engine.get_tick(vt_symbol)

        if direction == Direction.LONG:
            price = tick.ask_price_1 + contract.pricetick * payup
        else:
            price = tick.bid_price_1 - contract.pricetick * payup

        while True:
            order_volume: int = min(volume, max_volume)

            original_req: OrderRequest = OrderRequest(
                symbol=contract.symbol,
                exchange=contract.exchange,
                direction=direction,
                offset=offset,
                type=OrderType.LIMIT,
                price=price,
                volume=order_volume,
                reference=f"{APP_NAME}_Rollover"
            )

            req_list: List[OrderRequest] = self.main_engine.convert_order_request(
                original_req,
                contract.gateway_name,
                False,
                False
            )

            vt_orderids: list = []
            for req in req_list:
                vt_orderid: str = self.main_engine.send_order(req, contract.gateway_name)
                if not vt_orderid:
                    continue

                vt_orderids.append(vt_orderid)
                self.main_engine.update_order_request(req, vt_orderid, contract.gateway_name)

                msg: str = f"Commission {vt_symbol}, {direction.value}, {offset.value}, {volume}@{price}"
                self.write_log(msg)

            # Check whether all volume sent
            volume = volume - order_volume
            if not volume:
                break
