from .diagnosis import router as diagnosis_router
from .diagnosis_graph import router as graph_router
from .pet_care import router as pet_care_router

__all__ = ["diagnosis_router", "graph_router", "pet_care_router"]
