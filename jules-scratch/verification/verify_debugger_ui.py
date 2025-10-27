
import asyncio
from playwright.async_api import async_playwright, expect
import os

async def main():
    async with async_playwright() as p:
        # Launch Chromium with flags to enable WebGPU in a headless environment
        browser = await p.chromium.launch(args=[
            "--enable-unsafe-webgpu",
            "--enable-features=Vulkan",
            "--use-angle=vulkan",
        ])
        page = await browser.new_page()

        page.on("pageerror", lambda exc: print(f"--- BROWSER UNCAUGHT EXCEPTION --- \n{exc}"))

        file_path = os.path.abspath('pixel_vm_debugger.html')
        await page.goto(f'file://{file_path}')

        notes = page.locator("#notes")

        # 1. Verify Default WGSL View
        await expect(notes).to_contain_text("Compilation successful.", timeout=15000)
        await page.screenshot(path="jules-scratch/verification/01_default_view.png")

        # 2. Verify VM Run View
        await page.get_by_role("button", name="Run in VM").click()
        await expect(notes).to_contain_text("Assembled", timeout=10000)
        await asyncio.sleep(0.5)
        await page.screenshot(path="jules-scratch/verification/02_vm_view.png")

        # 3. Verify VM Debug View with Tooltip
        await page.get_by_role("button", name="Debug VM").click()
        await expect(notes).to_contain_text("Debugging VM memory", timeout=10000)

        debug_canvas = page.locator("#debug_canvas")
        await expect(debug_canvas).to_be_visible()

        await asyncio.sleep(0.5)

        await debug_canvas.hover(position={'x': 120, 'y': 150})
        await asyncio.sleep(0.5)

        tooltip = page.locator("#tooltip")
        await expect(tooltip).to_be_visible()
        await expect(tooltip).to_contain_text("Thread: [120, 150]")

        await page.screenshot(path="jules-scratch/verification/03_debug_view_with_tooltip.png")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
