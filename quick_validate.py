from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_skill_package(root: Path) -> list[str]:
    errors: list[str] = []
    skill_path = root / "SKILL.md"
    yaml_path = root / "agents" / "openai.yaml"
    readme_path = root / "README.md"

    for path in (skill_path, yaml_path, readme_path):
        if not path.is_file():
            errors.append(f"缺少必要文件：{path.relative_to(root)}")

    if not skill_path.is_file():
        return errors

    skill = read_text(skill_path)
    if not skill.startswith("---\n"):
        errors.append("SKILL.md 缺少 YAML frontmatter")
        return errors

    match = re.match(r"^---\n(.*?)\n---\n", skill, flags=re.DOTALL)
    if not match:
        errors.append("SKILL.md frontmatter 格式无效")
        return errors

    frontmatter = match.group(1)
    name_match = re.search(r"^name:\s*(\S+)\s*$", frontmatter, flags=re.MULTILINE)
    description_match = re.search(r"^description:\s*(.+?)\s*$", frontmatter, flags=re.MULTILINE)

    if not name_match:
        errors.append("frontmatter 缺少 name")
    elif name_match.group(1) != "make-knowledge-cards":
        errors.append("name 应为 make-knowledge-cards")

    if not description_match:
        errors.append("frontmatter 缺少 description")
    elif not description_match.group(1):
        errors.append("description 不能为空")

    required_sections = (
        "## 使用场景",
        "## 输入约定",
        "## 制作流程",
        "## 卡片格式",
        "## 数量与质量规则",
        "## 输出格式",
    )
    for section in required_sections:
        if section not in skill:
            errors.append(f"SKILL.md 缺少章节：{section}")

    if yaml_path.is_file():
        yaml_text = read_text(yaml_path)
        for field in ("display_name:", "short_description:", "default_prompt:"):
            if field not in yaml_text:
                errors.append(f"agents/openai.yaml 缺少字段：{field}")

    return errors


def validate_cards(text: str) -> list[str]:
    errors: list[str] = []
    card_headers = re.findall(r"^##\s+卡片\s+([0-9]+)[：:]", text, flags=re.MULTILINE)

    if not card_headers:
        errors.append("未找到任何知识卡片标题")
        return errors

    count = len(card_headers)
    if not 5 <= count <= 8:
        errors.append(f"卡片数量应为 5–8，实际为 {count}")

    expected = [str(number) for number in range(1, count + 1)]
    if card_headers != expected:
        errors.append("卡片编号应连续且从 1 开始")

    required_fields = (
        "核心知识",
        "简明解释",
        "例子/用例",
        "自测问题",
    )
    for index in range(1, count + 1):
        pattern = rf"^##\s+卡片\s+{index}[：:].*$"
        start = re.search(pattern, text, flags=re.MULTILINE)
        if not start:
            continue
        end_match = re.search(r"^##\s+卡片\s+" + str(index + 1) + r"[：:].*$", text[start.end():], flags=re.MULTILINE)
        if end_match:
            card_text = text[start.start(): start.end() + end_match.start()]
        else:
            card_text = text[start.start():]

        for field in required_fields:
            if f"**{field}：" not in card_text:
                errors.append(f"卡片 {index} 缺少字段：{field}")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="验证 make-knowledge-cards Skill 包")
    parser.add_argument(
        "--cards",
        type=Path,
        help="可选：验证已生成的知识卡片 Markdown 文件",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent
    errors = validate_skill_package(root)

    if args.cards:
        cards_path = args.cards
        if not cards_path.is_file():
            errors.append(f"卡片文件不存在：{cards_path}")
        else:
            errors.extend(validate_cards(read_text(cards_path)))

    if errors:
        print("验证失败：")
        for error in errors:
            print(f"- {error}")
        return 1

    print("验证通过：make-knowledge-cards Skill 包结构有效")
    if args.cards:
        print("验证通过：知识卡片格式有效（5–8 张且字段完整）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
