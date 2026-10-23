# 积木柜清单

由 `hotkey/core/catalog.json` 生成；修改积木后请重新生成本文档。

## 函数与数据（4）

| 积木 | id | 可用作 | 参数（类型 / 默认值） | Python |
|---|---|---|---|---|
| 设置变量 变量名 为 值或返回值 | `logic_set` | 语句 | name:code（变量名）, value:value（值或返回值） | `{name} = {value}` |
| 变量 变量名 增加 值 | `logic_change` | 语句 | name:code（变量名）, value:value = 1（值） | `{name} += {value}` |
| 定义函数 函数名（参数 a） | `logic_func_def` | 语句 | name:code（函数名）, params:code（a, b） | `def {name}({params}):` |
| 调用 函数名（参数） | `logic_func_plain` | 语句 | name:code（函数名）, args:code（参数） | `{name}({args})` |

## 流程控制（17）

| 积木 | id | 可用作 | 参数（类型 / 默认值） | Python |
|---|---|---|---|---|
| 等待 秒数 秒 | `flow_wait` | 语句 | seconds:number = 1（秒数，如 0.5） | `time.sleep({seconds})` |
| 如果 条件 那么 | `flow_if_else` | 语句 | condition:value（条件） | `if {condition}:` |
| 否则如果 条件 那么 | `flow_elif` | 语句 | condition:value（条件） | `elif {condition}:` |
| 当 条件 时重复 | `flow_while` | 语句 | condition:value（条件） | `while {condition}:` |
| 对 i 从 0 到 10 步长 1 重复 | `flow_for_range` | 语句 | name:code = i（i）, start:number = 0（0）, end:number = 10（10）, step:number = 1（1） | `for {name} in range({start}, {end}, {step}):` |
| 跳出循环 | `flow_break` | 语句 | — | `break` |
| 继续下一次循环 | `flow_continue` | 语句 | — | `continue` |
| 返回 返回值 | `flow_return` | 语句 | value:value（返回值） | `return {value}` |
| 变量 变量名 | `value_variable` | 值 | name:code（变量名） | `{name}` |
| (左值 ==、>、< 右值) | `value_compare` | 值 | left:code（左值）, operator:code = ==（==、>、<）, right:code（右值） | `({left} {operator} {right})` |
| (条件 and / or 条件) | `value_logic` | 值 | left:code（条件）, operator:code = and（and / or）, right:code（条件） | `({left} {operator} {right})` |
| 非 条件 | `value_not` | 值 | value:code（条件） | `not ({value})` |
| (左值 + - * / 右值) | `value_math` | 值 | left:code（左值）, operator:code = +（+ - * /）, right:code（右值） | `({left} {operator} {right})` |
| 随机整数 最小值 到 最大值 | `value_random` | 值 | low:number = 1（最小值）, high:number = 10（最大值） | `random.randint({low}, {high})` |
| 调用 函数名（参数） | `value_func_call` | 值 | name:code（函数名）, args:code（参数） | `{name}({args})` |
| Python 表达式 例如 x > 0 | `value_python` | 值 | code:code（例如 x > 0） | `{code}` |
| 图片 图片路径 是否存在 | `value_image_exists` | 值 | image:text（图片路径） | `pyautogui.locateOnScreen({image}) is not None` |

## 鼠标操作（11）

| 积木 | id | 可用作 | 参数（类型 / 默认值） | Python |
|---|---|---|---|---|
| 移动鼠标到（x, y） | `mouse_move_to` | 语句 | x:number（x）, y:number（y） | `pyautogui.moveTo({x}, {y})` |
| 相对移动鼠标（dx, dy） | `mouse_move_rel` | 语句 | dx:number（dx）, dy:number（dy） | `pyautogui.moveRel({dx}, {dy}, duration=0.3)` |
| 单击鼠标左键 | `mouse_click` | 语句 | — | `pyautogui.click()` |
| 双击鼠标左键 | `mouse_double_click` | 语句 | — | `pyautogui.doubleClick()` |
| 单击鼠标右键 | `mouse_right_click` | 语句 | — | `pyautogui.click(button='right')` |
| 鼠标左键按下 | `mouse_down` | 语句 | — | `pyautogui.mouseDown()` |
| 鼠标左键释放 | `mouse_up` | 语句 | — | `pyautogui.mouseUp()` |
| 鼠标滚轮向上滚 | `mouse_scroll_up` | 语句 | — | `pyautogui.scroll(10)` |
| 鼠标滚轮向下滚 | `mouse_scroll_down` | 语句 | — | `pyautogui.scroll(-10)` |
| 拖拽到（x, y） | `mouse_drag` | 语句 | x:number（x）, y:number（y） | `pyautogui.dragTo({x}, {y}, duration=0.5)` |
| 鼠标坐标（可当值） | `mouse_position` | 语句 / 值 | — | `pyautogui.position()` |

## 键盘操作（9）

| 积木 | id | 可用作 | 参数（类型 / 默认值） | Python |
|---|---|---|---|---|
| 按下 Enter | `key_press_enter` | 语句 | — | `pyautogui.press('enter')` |
| 输入文本「要输入的文本」 | `key_type_text` | 语句 | text:text（要输入的文本） | `pyautogui.typewrite({text})` |
| 逐字输入「要输入的文本」（间隔 0.1 秒） | `key_type_interval` | 语句 | text:text（要输入的文本） | `pyautogui.typewrite({text}, interval=0.1)` |
| 组合键 Ctrl+C | `key_hotkey_copy` | 语句 | — | `pyautogui.hotkey('ctrl', 'c')` |
| 组合键 Ctrl+V | `key_hotkey_paste` | 语句 | — | `pyautogui.hotkey('ctrl', 'v')` |
| 组合键 Alt+Tab | `key_hotkey_alt_tab` | 语句 | — | `pyautogui.hotkey('alt', 'tab')` |
| 组合键 Win+R | `key_hotkey_win_r` | 语句 | — | `pyautogui.hotkey('win', 'r')` |
| 按住 Shift | `key_down_shift` | 语句 | — | `pyautogui.keyDown('shift')` |
| 松开 Shift | `key_up_shift` | 语句 | — | `pyautogui.keyUp('shift')` |

## 屏幕操作（7）

| 积木 | id | 可用作 | 参数（类型 / 默认值） | Python |
|---|---|---|---|---|
| 截取全屏到 screenshot.png | `screen_screenshot` | 语句 | — | `pyautogui.screenshot('screenshot.png')` |
| 截取区域（x, y, w, h） | `screen_screenshot_region` | 语句 | left:number（x）, top:number（y）, width:number（w）, height:number（h） | `pyautogui.screenshot('region.png', region=({left}, {top}, {width}, {height}))` |
| 屏幕尺寸（可当值） | `screen_size` | 语句 / 值 | — | `pyautogui.size()` |
| 查找图片位置 图片路径（可当值） | `screen_locate` | 语句 / 值 | image:text（图片路径） | `pyautogui.locateOnScreen({image})` |
| 查找图片中心 图片路径（可当值） | `screen_locate_center` | 语句 / 值 | image:text（图片路径） | `pyautogui.locateCenterOnScreen({image})` |
| 坐标（x, y）颜色（可当值） | `screen_pixel` | 语句 / 值 | x:number（x）, y:number（y） | `pyautogui.pixel({x}, {y})` |
| 坐标（x, y）是否为颜色（R, G, B）（可当值） | `screen_pixel_matches` | 语句 / 值 | x:number（x）, y:number（y）, r:number（R）, g:number（G）, b:number（B） | `pyautogui.pixelMatchesColor({x}, {y}, ({r}, {g}, {b}))` |

## 弹窗交互（3）

| 积木 | id | 可用作 | 参数（类型 / 默认值） | Python |
|---|---|---|---|---|
| 弹出提示：提示文字 | `dialog_alert` | 语句 | text:text（提示文字） | `pyautogui.alert({text})` |
| 弹出确认框：提示文字（可当值） | `dialog_confirm` | 语句 / 值 | text:text（提示文字） | `pyautogui.confirm({text})` |
| 弹出输入框：提示文字（可当值） | `dialog_prompt` | 语句 / 值 | text:text（提示文字） | `pyautogui.prompt({text})` |

## 旧版隐藏积木

- `flow_if`：如果条件成立（True）（不在积木柜显示，旧配置兼容用）
- `flow_sleep_05`：等待 0.5 秒（不在积木柜显示，旧配置兼容用）
- `flow_sleep_1`：等待 1 秒（不在积木柜显示，旧配置兼容用）
- `flow_sleep_2`：等待 2 秒（不在积木柜显示，旧配置兼容用）
- `flow_sleep_5`：等待 5 秒（不在积木柜显示，旧配置兼容用）
- `flow_for_3`：重复执行 3 次（不在积木柜显示，旧配置兼容用）
- `logic_compare`：比较 左值 ==、>、< 右值 存入 结果变量（不在积木柜显示，旧配置兼容用）
- `logic_math`：计算 表达式 存入 结果变量（不在积木柜显示，旧配置兼容用）
- `logic_random`：随机整数 最小值 到 最大值 存入 结果变量（不在积木柜显示，旧配置兼容用）
- `logic_func_call`：调用 函数名（实参）存入 返回值变量（不在积木柜显示，旧配置兼容用）
- `logic_exists`：图片 图片路径 是否存在存入 结果变量（不在积木柜显示，旧配置兼容用）
- `logic_locate`：查找图片 图片路径 位置存入 结果变量（不在积木柜显示，旧配置兼容用）
- `logic_pixel`：坐标（x, y）颜色存入 结果变量（不在积木柜显示，旧配置兼容用）
- `logic_mouse_pos`：读取鼠标坐标存入 结果变量（不在积木柜显示，旧配置兼容用）
- `logic_screen_size`：读取屏幕尺寸存入 结果变量（不在积木柜显示，旧配置兼容用）
- `logic_return`：返回 返回值（不在积木柜显示，旧配置兼容用）

共 **51** 个可见积木，另有「空」块和 16 个隐藏旧积木。