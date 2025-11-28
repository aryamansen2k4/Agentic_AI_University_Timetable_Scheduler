from dataclasses import dataclass

@dataclass
class Course:
    id: str
    component: str  # "L", "T", "P"
    hours: float    # Float to support 1.5h classes
    group: str
    faculty: str
    is_core: bool = True  # Used for soft constraint optimization

@dataclass
class Room:
    id: str
    capacity: int
    type: str  # "Lecture", "Lab"

@dataclass
class Faculty:
    id: str
    name: str
    max_days: int
    allow_back_to_back: bool = True