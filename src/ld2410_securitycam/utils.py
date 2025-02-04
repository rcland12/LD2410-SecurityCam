import os
from ast import literal_eval
from typing import Any, Dict, Type

from ld2410_securitycam.logger import logger


class EnvArgumentParser:
    """
    A class for parsing environment variables as arguments with most Python types.
    """

    def __init__(self):
        self.dict: Dict[str, Any] = {}

    class _define_dict(dict):
        """
        A custom dictionary subclass for accessing arguments as attributes.
        """

        __getattr__ = dict.get
        __setattr__ = dict.__setitem__
        __delattr__ = dict.__delitem__

    def add_arg(self, variable: str, default: Any = None, d_type: Type = str) -> None:
        """
        Add an argument to be parsed from an environment variable.

        Args:
            variable (str): The name of the environment variable.
            default (Any): The default value if the environment variable is not set.
            d_type (Type): The expected data type of the argument. Defaults to str.
        """

        env = os.environ.get(variable)
        if env is None:
            try:
                if isinstance(default, d_type):
                    value = default
                else:
                    raise TypeError(
                        f"The default value for {variable} cannot be cast to the data type provided."
                    )
            except TypeError:
                raise TypeError(f"The type you provided for {variable} is not valid.")
        else:
            if callable(d_type):
                value = self._cast_type(env, d_type)
        self.dict[variable] = value

    @staticmethod
    def _cast_type(arg: str, d_type: Type) -> Any:
        """
        Cast the argument to the specified data type.

        Args:
            arg (str): The argument value as a string.
            d_type (Type): The desired data type.

        Returns:
            Any: The argument value casted to the specified data type.

        Raises:
            ValueError: If the argument does not match the given data type or is not supported.
        """

        if d_type in [list, tuple, bool, dict, set]:
            try:
                cast_value = literal_eval(arg)
                if not isinstance(cast_value, d_type):
                    raise TypeError(
                        f"The value cast type ({d_type}) does not match the value given for {arg}"
                    )
            except ValueError as e:
                raise ValueError(
                    f"Argument {arg} does not match given data type or is not supported:",
                    str(e),
                )
            except SyntaxError as e:
                raise SyntaxError(
                    f"Check the types entered for arugment {arg}:", str(e)
                )
        else:
            try:
                cast_value = d_type(arg)
            except ValueError as e:
                raise ValueError(
                    f"Argument {arg} does not match given data type or is not supported:",
                    str(e),
                )
            except SyntaxError as e:
                raise SyntaxError(
                    f"Check the types entered for arugment {arg}:", str(e)
                )

        return cast_value

    def parse_args(self) -> "_define_dict":
        """
        Parse the added arguments from the environment variables.

        Returns:
            _define_dict: A custom dictionary containing the parsed arguments.
        """

        return self._define_dict(self.dict)
