from app.outline_validator import validate_character_names

outline = """
第1集：代码被盗
林深发现周启明盗用了自己的代码。
苏曼选择站在周启明一边。
"""

known_names = ["林深", "苏曼", "周启明", "赵一鸣"]

result = validate_character_names(
    outline=outline,
    known_names=known_names
)

print(result)