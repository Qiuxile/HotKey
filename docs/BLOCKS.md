# 积木柜清单

由 `hotkey/core/catalog.json` 生成；修改积木后请重新生成本文档。

## 鼠标操作（11）

| 积木 | id | 参数 | 槽位 | Python |
|---|---|---|---|---|
| 移动鼠标到（x, y） | `mouse_move_to` | x:number（x）, y:number（y） | — | `pyautogui.moveTo({x}, {y})` |
| 相对移动鼠标（dx, dy） | `mouse_move_rel` | dx:number（dx）, dy:number（dy） | — | `pyautogui.moveRel({dx}, {dy}, duration=0.3)` |
| 单击鼠标左键 | `mouse_click` | — | — | `pyautogui.click()` |
| 双击鼠标左键 | `mouse_double_click` | — | — | `pyautogui.doubleClick()` |
| 单击鼠标右键 | `mouse_right_click` | — | — | `pyautogui.click(button='right')` |
| 鼠标左键按下 | `mouse_down` | — | — | `pyautogui.mouseDown()` |
| 鼠标左键释放 | `mouse_up` | — | — | `pyautogui.mouseUp()` |
| 鼠标滚轮向上滚 | `mouse_scroll_up` | — | — | `pyautogui.scroll(10)` |
| 鼠标滚轮向下滚 | `mouse_scroll_down` | — | — | `pyautogui.scroll(-10)` |
| 拖拽到（x, y） | `mouse_drag` | x:number（x）, y:number（y） | — | `pyautogui.dragTo({x}, {y}, duration=0.5)` |
| 读取鼠标坐标到变量 x, y | `mouse_position` | — | — | `x, y = pyautogui.position()` |

## 键盘操作（9）

| 积木 | id | 参数 | 槽位 | Python |
|---|---|---|---|---|
| 按下 Enter | `key_press_enter` | — | — | `pyautogui.press('enter')` |
| 输入文本「要输入的文本」 | `key_type_text` | text:text（要输入的文本） | — | `pyautogui.typewrite({text})` |
| 逐字输入「要输入的文本」（间隔 0.1 秒） | `key_type_interval` | text:text（要输入的文本） | — | `pyautogui.typewrite({text}, interval=0.1)` |
| 组合键 Ctrl+C | `key_hotkey_copy` | — | — | `pyautogui.hotkey('ctrl', 'c')` |
| 组合键 Ctrl+V | `key_hotkey_paste` | — | — | `pyautogui.hotkey('ctrl', 'v')` |
| 组合键 Alt+Tab | `key_hotkey_alt_tab` | — | — | `pyautogui.hotkey('alt', 'tab')` |
| 组合键 Win+R | `key_hotkey_win_r` | — | — | `pyautogui.hotkey('win', 'r')` |
| 按住 Shift | `key_down_shift` | — | — | `pyautogui.keyDown('shift')` |
| 松开 Shift | `key_up_shift` | — | — | `pyautogui.keyUp('shift')` |

## 屏幕操作（7）

| 积木 | id | 参数 | 槽位 | Python |
|---|---|---|---|---|
| 截取全屏到 screenshot.png | `screen_screenshot` | — | — | `pyautogui.screenshot('screenshot.png')` |
| 截取区域（左 左，上 上，宽 宽，高 高） | `screen_screenshot_region` | left:number（左）, top:number（上）, width:number（宽）, height:number（高） | — | `pyautogui.screenshot('region.png', region=({left}, {top}, {width}, {height}))` |
| 读取屏幕尺寸到变量 w, h | `screen_size` | — | — | `w, h = pyautogui.size()` |
| 在屏幕上查找图片「图片路径」 | `screen_locate` | image:text（图片路径） | — | `pyautogui.locateOnScreen({image})` |
| 查找图片并取中心坐标「图片路径」 | `screen_locate_center` | image:text（图片路径） | — | `pyautogui.locateCenterOnScreen({image})` |
| 读取坐标（x, y）的颜色 | `screen_pixel` | x:number（x）, y:number（y） | — | `pyautogui.pixel({x}, {y})` |
| 判断（x, y）是否为颜色（R, G, B） | `screen_pixel_matches` | x:number（x）, y:number（y）, r:number（R）, g:number（G）, b:number（B） | — | `pyautogui.pixelMatchesColor({x}, {y}, ({r}, {g}, {b}))` |

## 函数与数据（13）

| 积木 | id | 参数 | 槽位 | Python |
|---|---|---|---|---|
| 设置变量 变量名 为 值或表达式 | `logic_set` | name:code（变量名）, value:code（值或表达式） | — | `{name} = {value}` |
| 比较 左值 ==、>、< 右值 存入 结果变量 | `logic_compare` | left:code（左值）, operator:code（==、>、<）, right:code（右值）, variable:code（结果变量） | — | `{variable} = ({left} {operator} {right})` |
| 计算 表达式 存入 结果变量 | `logic_math` | expression:code（表达式，如 x + 1）, variable:code（结果变量） | — | `{variable} = {expression}` |
| 随机整数 最小值 到 最大值 存入 结果变量 | `logic_random` | low:number（最小值）, high:number（最大值）, variable:code（结果变量） | — | `{variable} = random.randint({low}, {high})` |
| 定义函数 函数名（参数 参数）返回 返回表达式 | `logic_func_def` | name:code（函数名）, params:code（参数，如 a, b）, result:code（返回表达式，可留空） | 函数体 | `def {name}({params}):` |
| 调用 函数名（实参）存入 返回值变量 | `logic_func_call` | name:code（函数名）, args:code（实参）, variable:code（返回值变量） | — | `{variable} = {name}({args})` |
| 调用 函数名（实参） | `logic_func_plain` | name:code（函数名）, args:code（实参） | — | `{name}({args})` |
| 返回 返回值 | `logic_return` | value:code（返回值） | — | `return {value}` |
| 图片 图片路径 是否存在存入 结果变量 | `logic_exists` | image:text（图片路径）, variable:code（结果变量） | — | `{variable} = pyautogui.locateOnScreen({image}) is not None` |
| 查找图片 图片路径 位置存入 结果变量 | `logic_locate` | image:text（图片路径）, variable:code（结果变量） | — | `{variable} = pyautogui.locateCenterOnScreen({image})` |
| 坐标（x, y）颜色存入 结果变量 | `logic_pixel` | x:number（x）, y:number（y）, variable:code（结果变量） | — | `{variable} = pyautogui.pixel({x}, {y})` |
| 读取鼠标坐标存入 结果变量 | `logic_mouse_pos` | variable:code（结果变量） | — | `{variable} = pyautogui.position()` |
| 读取屏幕尺寸存入 结果变量 | `logic_screen_size` | variable:code（结果变量） | — | `{variable} = pyautogui.size()` |

## 弹窗交互（3）

| 积木 | id | 参数 | 槽位 | Python |
|---|---|---|---|---|
| 弹出提示：提示文字 | `dialog_alert` | text:text（提示文字） | — | `pyautogui.alert({text})` |
| 弹出确认框：提示文字 | `dialog_confirm` | text:text（提示文字） | — | `pyautogui.confirm({text})` |
| 弹出输入框：提示文字 | `dialog_prompt` | text:text（提示文字） | — | `pyautogui.prompt({text})` |

## 流程控制（6）

| 积木 | id | 参数 | 槽位 | Python |
|---|---|---|---|---|
| 等待 0.5 秒 | `flow_sleep_05` | — | — | `time.sleep(0.5)` |
| 等待 1 秒 | `flow_sleep_1` | — | — | `time.sleep(1)` |
| 等待 2 秒 | `flow_sleep_2` | — | — | `time.sleep(2)` |
| 等待 5 秒 | `flow_sleep_5` | — | — | `time.sleep(5)` |
| 重复执行 3 次 | `flow_for_3` | — | 重复内容 | `for i in range(3):` |
| 如果 条件 那么 | `flow_if_else` | condition:code（条件，例如 x > 0） | 那么 / 否则 | `if {condition}:` |

## 旧版隐藏积木

- `flow_if`：如果条件成立（True）（不在积木柜显示，旧配置迁移用）

共 **49** 个可见积木，另有「空」块和 1 个隐藏旧积木。