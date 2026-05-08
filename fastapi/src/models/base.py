from pydantic import BaseModel, ConfigDict


class SchemaBase(BaseModel):
    """
    Базовый класс для всех схем Pydantic в проекте.

    Настраивает общие параметры для всех моделей:
    - from_attributes: Позволяет создавать модели из атрибутов объектов.
    - populate_by_name: Позволяет использовать как alias, так и имя поля.
    - str_strip_whitespace: Автоматически удаляет пробелы из строк.
    """
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )
