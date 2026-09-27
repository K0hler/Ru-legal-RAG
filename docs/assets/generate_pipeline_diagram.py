"""Render the labeled Legal RAG architecture diagram as a PNG."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "legal-rag-pipeline-labeled.png"
FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")
BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")

im = Image.new("RGB", (2400, 1390), "#f7f9fc")
d = ImageDraw.Draw(im)
f_title = ImageFont.truetype(str(BOLD), 57)
f_section = ImageFont.truetype(str(BOLD), 31)
f_head = ImageFont.truetype(str(BOLD), 27)
f_body = ImageFont.truetype(str(FONT), 22)
f_small = ImageFont.truetype(str(FONT), 19)


def txt(x, y, value, font, fill="#1b293c"):
    d.multiline_text((x, y), value, font=font, fill=fill, spacing=7)


def arrow(points, color="#66809b", width=6, head=15):
    d.line(points, fill=color, width=width, joint="curve")
    x1, y1 = points[-2]
    x2, y2 = points[-1]
    if x2 > x1:
        tip = [(x2, y2), (x2 - head, y2 - head // 2), (x2 - head, y2 + head // 2)]
    elif x2 < x1:
        tip = [(x2, y2), (x2 + head, y2 - head // 2), (x2 + head, y2 + head // 2)]
    elif y2 > y1:
        tip = [(x2, y2), (x2 - head // 2, y2 - head), (x2 + head // 2, y2 - head)]
    else:
        tip = [(x2, y2), (x2 - head // 2, y2 + head), (x2 + head // 2, y2 + head)]
    d.polygon(tip, fill=color)


def box(x, y, w, h, number, heading, lines, fill, border):
    d.rounded_rectangle((x + 4, y + 5, x + w + 4, y + h + 5), radius=22, fill="#dfe6ef")
    d.rounded_rectangle((x, y, x + w, y + h), radius=22, fill=fill, outline=border, width=3)
    d.rounded_rectangle((x + 18, y + 16, x + 67, y + 58), radius=12, fill=border)
    tw = d.textbbox((0, 0), str(number), font=f_head)[2]
    txt(x + 42 - tw / 2, y + 20, str(number), f_head, "#ffffff")
    txt(x + 20, y + 71, heading, f_head)
    txt(x + 20, y + 112, lines, f_body, "#46586c")


txt(60, 28, "Legal RAG: от источника к проверенному ответу", f_title)
txt(61, 103, "Целевая архитектура • состояние на 21.09.2026", f_body, "#52677e")

d.rounded_rectangle((35, 149, 2365, 431), radius=27, fill="#eaf5f2")
txt(59, 155, "I. КОМПИЛЯЦИЯ НОРМАТИВНОГО КОРПУСА", f_section, "#126a61")
top = [
    ("Исходный НПА", "файл + URL\nпубликации"),
    ("Manifest", "хеш, реквизиты,\nстатус, даты"),
    ("Извлечение", "текст, таблицы,\nстраницы, координаты"),
    ("Очистка + парсер", "LegalStructureParser\nюридическая иерархия"),
    ("Нормы и редакции", "Act → Edition →\nProvision"),
    ("SearchChunk", "фрагмент поиска,\nпривязанный к норме"),
    ("Индексы", "FTS + embeddings\nс метаданными"),
]
for i, (heading, lines) in enumerate(top):
    box(55 + 335 * i, 213, 280, 183, i + 1, heading, lines, "#ffffff", "#238479")
    if i < 6:
        arrow([(335 + 335 * i, 304), (381 + 335 * i, 304)], "#238479")

d.rounded_rectangle((35, 464, 2365, 839), radius=27, fill="#eaf1fb")
txt(59, 475, "II. ВОПРОС → ПРИМЕНИМОЕ ПРАВО", f_section, "#275d9b")
middle = [
    ("Вопрос", "текст + дата\nсобытия"),
    ("Нормализация", "реквизиты, дата,\nюрисдикция"),
    ("Фильтр до поиска", "редакция, статус,\nscope, ACL"),
    ("search_legal", "лексический +\nвекторный поиск"),
    ("Ранжирование", "RRF → дедупликация →\nrerank кандидатов"),
    ("Контекст и ссылки", "полная норма +\ncitation handles"),
]
for i, (heading, lines) in enumerate(middle):
    box(55 + 390 * i, 584, 340, 211, i + 1, heading, lines, "#ffffff", "#427bb8")
    if i < 5:
        arrow([(395 + 390 * i, 689), (442 + 390 * i, 689)], "#427bb8")

# Search projections feed retrieval; canonical provisions also support exact lookup.
arrow([(2210, 396), (2210, 449), (1395, 449), (1395, 584)], "#238479", 5)
txt(1445, 418, "индексы → поиск", f_small, "#126a61")
arrow([(1535, 396), (1535, 443), (2165, 443), (2165, 584)], "#9a6c2c", 4)
txt(1730, 447, "точный get_provision", f_small, "#875c21")

d.rounded_rectangle((35, 869, 2365, 1242), radius=27, fill="#f5f0e8")
txt(59, 881, "III. ОТВЕТ В ПРИЛОЖЕНИИ И КОНТРОЛЬ", f_section, "#8e5b20")
bottom = [
    ("Материалы дела", "факты, документы,\nпроисхождение"),
    ("Backend", "состояние дела,\nправа доступа"),
    ("Память", "контекст диалога,\nне источник права"),
    ("Агент", "ответ по источникам\nс [CIT:id]"),
    ("verify_citations", "ссылка, дата, цитата;\nсмысл — отдельно"),
    ("Результат", "ответ с источниками\n/ уточнение / отказ"),
]
for i, (heading, lines) in enumerate(bottom):
    fill = "#ffffff" if i < 3 else "#fffdfa"
    box(55 + 390 * i, 984, 340, 211, i + 1, heading, lines, fill, "#ba863f")
for i in (0, 1, 2):
    x = 225 + 390 * i
    d.line([(x, 984), (x, 948), (1395, 948)], fill="#ba863f", width=4)
arrow([(1395, 948), (1395, 984)], "#ba863f", 4)
arrow([(2180, 795), (2180, 847), (1395, 847), (1395, 948)], "#427bb8", 5)
arrow([(1565, 1089), (1612, 1089)], "#ba863f")
arrow([(1955, 1089), (2002, 1089)], "#ba863f")

txt(58, 1264, "СЕЙЧАС: LAW_Data и JKH имеют отдельные FTS-индексы; чат JKH ищет материалы дела.", f_body, "#33455a")
txt(58, 1303, "ЦЕЛЬ: редакции и нормы → фильтры до поиска → citation handles → проверенный ответ.", f_body, "#33455a")
txt(58, 1341, "Точный get_provision обходит embeddings и rerank; проверка смысла вывода — отдельный этап.", f_small, "#52677e")

im.save(OUT, optimize=True)
print(OUT)
