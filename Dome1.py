import pyautogui
import cv2
import numpy as np
import time
import logging
from typing import Optional, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class ImageNotFoundError(Exception):
    """自定义图像未找到异常"""
    pass


# 截取屏幕
        # 表示该方法返回的是一个NumPy 多维数组（即图像矩阵），这是 OpenCV 的标准图像格式。
def capture_screen() -> np.ndarray:
    """捕获当前屏幕并返回OpenCV格式图像"""
    try:
        # 捕获当前屏幕
        screenshot = pyautogui.screenshot()
        # 返回OpenCV格式图像
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    except Exception as e:
        # 如果截不了屏就抛出异常
        logging.error("屏幕捕获失败: %s", e)
        raise


# 负责执行具体的模板匹配
def find_template(screenshot: np.ndarray,
                  template_path: str,
                  threshold: float = 0.6) -> Optional[Tuple[int, int]]:
    """
    单次模板匹配
    :param screenshot: 屏幕截图（BGR格式）
    :param template_path: 模板图片路径
    :param threshold: 匹配阈值
    :return: (中心x, 中心y) 坐标或None
    """
    try:
        # 读取模板图片
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            raise ImageNotFoundError(f"模板文件不存在: {template_path}")

        # 预处理图像
        gray_screen = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        template_h, template_w = template.shape

        # 执行模板匹配
        result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val < threshold:
            logging.debug("匹配失败: %.2f < %.2f @ %s", max_val, threshold, template_path)
            return None

        # 计算中心坐标
        top_left = max_loc
        center_x = top_left[0] + template_w // 2
        center_y = top_left[1] + template_h // 2
        return (center_x, center_y)

    except Exception as e:
        logging.error("模板匹配异常: %s", e)
        return None


# 负责多次循环寻找
def find_button(template_path: str,
                max_attempts: int = 3, # 最多寻找3次
                interval: float = 1.0,
                threshold: float = 0.7) -> Optional[Tuple[int, int]]:
    """
    带重试机制的按钮查找
    :param template_path: 模板图片路径
    :param max_attempts: 最大尝试次数
    :param interval: 重试间隔(秒)
    :param threshold: 匹配阈值
    """
    # for循环来实现最大重试次数
    for attempt in range(1, max_attempts + 1):
        try:
            screenshot = capture_screen()
            # find_template为具体执行匹配模板的函数
            position = find_template(screenshot, template_path, threshold)
            if position:
                logging.info("成功匹配: %s (尝试次数: %d)", template_path, attempt)
                # 找到后，返回该按钮具体的坐标值
                return position

            logging.warning("匹配失败: %s (第%d次尝试)", template_path, attempt)
            if attempt < max_attempts:
                time.sleep(interval)

        except Exception as e:
            logging.error("查找按钮异常: %s", e)
            break

    logging.error("超过最大尝试次数: %s", template_path)
    return None


def click_position(position: Tuple[int, int],
                   clicks: int = 1,
                   move_duration: float = 0.3,
                   interval: float = 0.2) -> None:
    """
    模拟鼠标点击
    :param position: (x, y) 坐标
    :param clicks: 点击次数
    :param move_duration: 鼠标移动耗时
    :param interval: 点击间隔时间
    """
    try:
        # 读取坐标
        x, y = position
        # 移动鼠标到目标位置
        pyautogui.moveTo(x, y, duration=move_duration)

        # 执行鼠标点击,clicks为点击次数
        for _ in range(clicks):
            pyautogui.click()
            # interval为点击间隔时间
            time.sleep(interval)
        logging.info("已执行点击: (%d, %d)", x, y)

    except Exception as e:
        logging.error("点击操作失败: %s", e)


def auto_click(template_path: str,
               max_attempts: int = 3,
               click_times: int = 1,
               success_delay: float = 1.0,
               **find_kwargs) -> bool:
    """
    :param template_path: 模板图片路径
    :param max_attempts: 查找按钮的最大尝试次数
    :param click_times: 点击次数
    :param success_delay: 点击后等待时间（秒）
    :param find_kwargs: 传递给 find_button 的额外参数
    :return: 是否成功执行
    """
    # 调用前面已经封装好的find_button方法,获得按钮所在坐标
    position = find_button(template_path, max_attempts, **find_kwargs)
    if not position:
        return False
    # 把坐标信息传入到点击方法中,开始点击
    click_position(position, clicks=click_times)
    # 让界面sleep,确保在动画结束后再搜索按钮
    time.sleep(success_delay)  # 确保界面稳定
    return True


# -------------------- 业务逻辑 --------------------
def main_workflow():
    """主业务流程"""
    # 初始化等待
    time.sleep(1)

    # 领取活动费
    auto_click("template_path/ActivityFee.png")
    # 关闭弹窗
    auto_click("template_path/Close.png")

    # 处理工作任务
    if not auto_click("template_path/Work.png"):
        auto_click("template_path/Work-1.png")
    # 执行工作流程
    def job_flow(job_number: int):
        """单个工作流程"""
        if not auto_click(f"template_path/SelectJob{job_number}.png"):
            return
        auto_click("template_path/Select.png")
        auto_click("template_path/Decision2.png")
        auto_click("template_path/Start.png")
    job_flow(1)
    time.sleep(3)
    job_flow(2)
    auto_click("template_path/Home.png")

    # 执行商店逻辑
    auto_click("template_path/Shop.png")
    # 打开每日商店
    auto_click("template_path/DailyExchangeOffice.png")
    # 选择おすすめ
    auto_click("template_path/Recommendation.png")
    # 点击决定,购买
    auto_click("template_path/Decision.png")
    # 跳转到AP商店
    auto_click("template_path/AP.png")
    # 购买AP商品
    auto_click("template_path/PtUp.png")
    auto_click("template_path/Decision.png")
    auto_click("template_path/NoteUp.png")
    auto_click("template_path/Decision.png")
    auto_click("template_path/TryAgainTicket.png")
    auto_click("template_path/Decision.png")
    auto_click("template_path/RegenerationTicket.png")
    auto_click("template_path/Decision.png")
    # 购买结束回到home
    auto_click("template_path/Home.png")

    # 开始执行升一级支援卡逻辑
    auto_click("template_path/Idol.png")
    auto_click("template_path/SupportCard.png")
    # 默认按等级顺序,点击变成倒序
    auto_click("template_path/Sort.png")
    # 选中任一1级卡
    auto_click("template_path/Lv1.png")
    # 点开详细界面
    auto_click("template_path/Detailed.png")
    # 选择强化
    auto_click("template_path/LvStrengthen.png")
    auto_click("template_path/LvStrengthen.png")
    # 强化结束回到home
    auto_click("template_path/Home.png")

    # 开始收尾逻辑
    # 领取每日任务奖励
    auto_click("template_path/Mission.png")
    auto_click("template_path/Lump-sumCollection.png")
    auto_click("template_path/Close.png")
    auto_click("template_path/X.png")
    auto_click("template_path/Home.png")
    # 领取邮箱
    auto_click("template_path/Present.png")
    auto_click("template_path/Lump-sumCollection.png")
    auto_click("template_path/Close.png")
    auto_click("template_path/Home.png")


if __name__ == "__main__":
    try:
        main_workflow()
        logging.info("流程执行完成")
    except KeyboardInterrupt:
        logging.warning("用户中断执行")
    except Exception as e:
        logging.exception("程序异常终止: %s", e)