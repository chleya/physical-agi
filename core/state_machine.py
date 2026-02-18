"""
状态机模块
完全解耦，可独立使用
"""

from typing import Dict, List, Optional, Callable, Any
from enum import Enum, auto
from dataclasses import dataclass


class State(Enum):
    """状态枚举"""
    IDLE = auto()
    EXPLORING = auto()
    MOVING = auto()
    AVOIDING = auto()
    COLLABORATING = auto()
    RESTING = auto()
    ERROR = auto()


@dataclass
class Transition:
    """状态转换"""
    from_state: State
    to_state: State
    condition: Callable[[], bool]
    action: Optional[Callable[[], None]] = None


class StateMachine:
    """
    有限状态机 (FSM)
    
    特点:
    - 完全解耦
    - 支持条件转换
    - 支持进入/退出动作
    - 可序列化
    """
    
    def __init__(self, 
                 initial_state: State = State.IDLE,
                 name: str = "StateMachine"):
        self.name = name
        self.current_state = initial_state
        self.previous_state: Optional[State] = None
        self.state_time: float = 0.0
        
        # 状态回调
        self.on_enter: Dict[State, List[Callable]] = {}
        self.on_exit: Dict[State, List[Callable]] = {}
        self.on_update: Dict[State, Callable[[], None]] = {}
        
        # 转换规则
        self.transitions: List[Transition] = []
        
        # 历史
        self.history: List[Dict] = []
    
    def add_transition(self, 
                      from_state: State,
                      to_state: State,
                      condition: Callable[[], bool],
                      action: Optional[Callable[[], None]] = None) -> None:
        """
        添加状态转换
        
        Args:
            from_state: 源状态
            to_state: 目标状态
            condition: 触发条件
            action: 执行动作
        """
        self.transitions.append(Transition(
            from_state=from_state,
            to_state=to_state,
            condition=condition,
            action=action
        ))
    
    def on_enter_state(self, state: State) -> Callable:
        """装饰器：进入状态动作"""
        def decorator(func: Callable) -> Callable:
            if state not in self.on_enter:
                self.on_enter[state] = []
            self.on_enter[state].append(func)
            return func
        return decorator
    
    def on_exit_state(self, state: State) -> Callable:
        """装饰器：退出状态动作"""
        def decorator(func: Callable) -> Callable:
            if state not in self.on_exit:
                self.on_exit[state] = []
            self.on_exit[state].append(func)
            return func
        return decorator
    
    def on_update_state(self, state: State) -> Callable:
        """装饰器：状态更新动作"""
        def decorator(func: Callable) -> Callable:
            self.on_update[state] = func
            return func
        return decorator
    
    def transition_to(self, 
                      new_state: State,
                      force: bool = False) -> bool:
        """
        尝试转换到新状态
        
        Args:
            new_state: 目标状态
            force: 强制转换（跳过条件检查）
            
        Returns:
            是否成功转换
        """
        if new_state == self.current_state:
            return False
        
        if not force:
            # 检查是否有有效的转换规则
            valid = False
            for trans in self.transitions:
                if (trans.from_state == self.current_state and 
                    trans.to_state == new_state and 
                    trans.condition()):
                    valid = True
                    break
            
            if not valid:
                return False
        
        # 退出旧状态
        if self.current_state in self.on_exit:
            for callback in self.on_exit[self.current_state]:
                callback()
        
        # 记录历史
        self.history.append({
            'from': self.current_state,
            'to': new_state,
            'time': self.state_time
        })
        
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_time = 0.0
        
        # 进入新状态
        if new_state in self.on_enter:
            for callback in self.on_enter[new_state]:
                callback()
        
        return True
    
    def update(self, dt: float) -> None:
        """
        更新状态机
        
        Args:
            dt: 时间步长
        """
        self.state_time += dt
        
        # 执行状态更新动作
        if self.current_state in self.on_update:
            self.on_update[self.current_state]()
        
        # 检查转换条件
        for trans in self.transitions:
            if trans.from_state == self.current_state:
                if trans.condition():
                    if self.transition_to(trans.to_state):
                        if trans.action:
                            trans.action()
                        break
    
    def get_state(self) -> State:
        """获取当前状态"""
        return self.current_state
    
    def is_in(self, state: State) -> bool:
        """检查是否在指定状态"""
        return self.current_state == state
    
    def serialize(self) -> Dict:
        """序列化"""
        return {
            'name': self.name,
            'current_state': self.current_state.name,
            'previous_state': self.previous_state.name if self.previous_state else None,
            'state_time': self.state_time
        }


class BehaviorStateMachine(StateMachine):
    """
    行为状态机
    
    预定义常见行为状态和转换
    """
    
    def __init__(self, name: str = "BehaviorFSM"):
        super().__init__(initial_state=State.IDLE, name=name)
        
        # 定义行为转换
        self._setup_behaviors()
    
    def _setup_behaviors(self):
        """设置标准行为"""
        
        # IDLE -> EXPLORING
        self.add_transition(
            from_state=State.IDLE,
            to_state=State.EXPLORING,
            condition=lambda: True,  # 总是可以开始探索
            action=lambda: print("Starting exploration")
        )
        
        # EXPLORING -> MOVING
        self.add_transition(
            from_state=State.EXPLORING,
            to_state=State.MOVING,
            condition=lambda: False,  # 子类实现
        )
        
        # ANY -> AVOIDING (紧急转换)
        self.add_transition(
            from_state=State.IDLE,
            to_state=State.AVOIDING,
            condition=lambda: False,  # 子类实现
        )
        
        # ANY -> RESTING
        self.add_transition(
            from_state=State.IDLE,
            to_state=State.RESTING,
            condition=lambda: False,  # 子类实现
        )


# ========== 独立测试 ==========
if __name__ == "__main__":
    # 创建状态机
    fsm = StateMachine(initial_state=State.IDLE, name="TestFSM")
    
    # 添加转换
    fsm.add_transition(
        from_state=State.IDLE,
        to_state=State.EXPLORING,
        condition=lambda: True
    )
    
    fsm.add_transition(
        from_state=State.EXPLORING,
        to_state=State.MOVING,
        condition=lambda: True
    )
    
    # 设置回调
    @fsm.on_enter_state(State.EXPLORING)
    def on_explore():
        print("Entering EXPLORING state")
    
    @fsm.on_exit_state(State.EXPLORING)
    def on_stop_explore():
        print("Leaving EXPLORING state")
    
    @fsm.on_update_state(State.MOVING)
    def update_move():
        print("Moving...")
    
    # 测试
    print("状态机测试:")
    print(f"初始状态: {fsm.get_state().name}")
    
    fsm.update(0.016)
    print(f"更新后状态: {fsm.get_state().name}")
    
    fsm.transition_to(State.MOVING)
    print(f"转换后状态: {fsm.get_state().name}")
    
    print(f"\n历史记录: {fsm.history}")
    print(f"\n序列化: {fsm.serialize()}")
