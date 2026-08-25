class breaker():
    
    """
    r_voltage: int = 0
    max_voltage: int = 0
    
    r_current: int = 0
    short_current: int = 0

    r_frequency: int = 0

    max_op_temperature: int = 0
    min_op_temperature: int = 0
    """

    def __init__(
        self,
        r_frequency:int,
        r_voltage:int,max_voltage:int,
        r_current:int,short_current:int,
        max_op_temperature:int,min_op_temperature:int,
        brand:str="unspecified",model:str="unspecified"
        ) -> None:

        op_temperature:list[int] = [min_op_temperature,max_op_temperature]  # pyright: ignore[reportUnusedVariable]

        return
        
    def load_curve(self):
        pass

    def temp_curve(self):
        pass

