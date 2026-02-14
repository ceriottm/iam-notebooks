from typing import List, Union

from ipywidgets import Widget
from traitlets.utils.sentinel import Sentinel


class CueWidget:
    """
    Observes a list of traits of widgets and sets cue when one of the widgets' traits
    change. The behavior when the cue is set has to be implemented by children class.

    :param widgets_to_observe:
        The widget to observe if the `traits_to_observe` has changed.
    :param traits_to_observe:
        The trait from the `widgets_to_observe` to observe if changed.
        Specify `traitlets.All` to observe all traits.
    :param cued:
        Specifies if it is cued on initialization
    """

    def __init__(
        self,
        widgets_to_observe: Union[List[Widget], Widget, None] = None,
        traits_to_observe: Union[
            str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = "value",
        cued: bool = True,
        *args,
        **kwargs,
    ):
        self._widgets_to_observe: List[Widget] = []
        self._traits_to_observe: List[Union[str, Sentinel, List[str]]] = []
        if widgets_to_observe is not None:
            # normal usage (your explicit calls)
            self.set_widgets_to_observe(widgets_to_observe, traits_to_observe)

        self.cued = cued

    @property
    def widgets_to_observe(self) -> List[Widget]:
        return self._widgets_to_observe

    def set_widgets_to_observe(
        self,
        widgets_to_observe: Union[List[Widget], Widget],
        traits_to_observe: Union[
            str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = "value",
    ):
        self.unobserve_widgets()

        if not (isinstance(widgets_to_observe, list)):
            widgets_to_observe = [widgets_to_observe]
            if isinstance(traits_to_observe, list):
                for trait in traits_to_observe:
                    if isinstance(trait, list):
                        raise ValueError(
                            "traits_to_observe cannot contain lists when "
                            "widgets_to_observe is not a list."
                        )
            traits_to_observe = [traits_to_observe]  # type: ignore[list-item]
        else:
            if not (isinstance(traits_to_observe, list)):
                raise ValueError(
                    "widgets_to_observe cannot be list when "
                    "traits_to_observe is not a list"
                )

        if len(widgets_to_observe) != len(traits_to_observe):
            raise ValueError(
                "widgets_to_observe and traits_to_observe and"
                "must have the same length."
            )

        self._widgets_to_observe = widgets_to_observe
        self._traits_to_observe = traits_to_observe

        self.observe_widgets()

    @property
    def traits_to_observe(self) -> List[Union[str, List[str], Sentinel]]:
        return self._traits_to_observe

    def observe_widgets(self):
        unique_widget_trait_pairs = set(
            [
                (self._widgets_to_observe[i], self._traits_to_observe[i])
                for i in range(len(self._widgets_to_observe))
            ]
        )
        for widget, trait in unique_widget_trait_pairs:
            widget.observe(self._on_trait_to_observe_changed, trait)

    def unobserve_widgets(self):
        unique_widget_trait_pairs = set(
            [
                (self._widgets_to_observe[i], self._traits_to_observe[i])
                for i in range(len(self._widgets_to_observe))
            ]
        )
        for widget, trait in unique_widget_trait_pairs:
            widget.unobserve(self._on_trait_to_observe_changed, trait)

    @property
    def cued(self) -> bool:
        raise NotImplementedError("cue behavior has not been implemented")

    @cued.setter
    def cued(self, cued: bool):
        raise NotImplementedError("cue behavior has not been implemented")

    def _on_trait_to_observe_changed(self, change: dict):
        self.cued = True
