__all__ = ["AnalysisEngine"]


def __getattr__(name: str):
	if name == "AnalysisEngine":
		from tcs_smart_analyzer.core.engine import AnalysisEngine

		return AnalysisEngine
	raise AttributeError(name)
