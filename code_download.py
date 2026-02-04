import asyncio
import aiohttp
import os
try:
    from pinterest_downloader import *  # type: ignore
except Exception:
    async def download_pinterest_media(pin_url: str, return_url: bool = True):
        """
        Fallback minimal extractor: fetches the pin page and tries to extract a media url.
        Returns {'success': bool, 'url': str|None, 'type': 'video'|'image'|None}
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.get(pin_url) as resp:
                    if resp.status != 200:
                        return {"success": False, "url": None, "type": None}
                    html = await resp.text()
        except Exception:
            return {"success": False, "url": None, "type": None}

        import re

        # Prefer video: look for og:video or contentUrl
        vid = None
        m = re.search(r'<meta[^>]+property="og:video"[^>]+content="([^"]+)"', html)
        if m:
            vid = m.group(1)
        if not vid:
            m = re.search(r'"contentUrl"\s*:\s*"(https?:[^"\\]+\.mp4)"', html)
            if m:
                vid = m.group(1)

        if vid:
            return {"success": True, "url": vid, "type": "video"}

        # Fallback to image: og:image or images field
        img = None
        m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        if m:
            img = m.group(1)
        if not img:
            m = re.search(r'"images"\s*:\s*\{[^}]*"orig"\s*:\s*\{[^}]*"url"\s*:\s*"(https?:[^"\\]+)"', html)
            if m:
                img = m.group(1)

        if img:
            return {"success": True, "url": img, "type": "image"}

        return {"success": False, "url": None, "type": None}

async def download_file(url, filename):
    """Download a file from URL and save it to disk"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(filename, 'wb') as f:
                        f.write(content)
                    print(f"✓ Downloaded: {filename}")
                    return True
                else:
                    print(f"✗ Failed to download: Status {response.status}")
                    return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

async def download_pinterest(pin_id, save_location, filename=None):
    """
    Download a Pinterest pin by ID
    
    Args:
        pin_id: Pinterest pin ID or full URL
        save_location: Directory path where file will be saved
        filename: Optional custom filename (without extension)
    
    Returns:
        dict: {'success': bool, 'filepath': str, 'type': str}
    """
    # Create directory if it doesn't exist
    os.makedirs(save_location, exist_ok=True)
    
    # Handle both URLs and IDs
    if not pin_id.startswith('http'):
        pin_url = f"https://www.pinterest.com/pin/{pin_id}/"
    else:
        pin_url = pin_id
    
    print(f"Fetching: {pin_url}")
    
    # Get media URL
    result = await download_pinterest_media(pin_url, return_url=True)
    
    if not result['success']:
        print("✗ Failed to get media URL")
        return {'success': False, 'filepath': None, 'type': None}
    
    # Determine file extension
    media_type = result['type']
    ext = '.mp4' if media_type == 'video' else '.jpg'
    
    # Generate filename
    if filename is None:
        filename = f"pin_{pin_id.split('/')[-2] if '/' in pin_id else pin_id}"
    
    filepath = os.path.join(save_location, f"{filename}{ext}")
    
    # Download the file
    success = await download_file(result['url'], filepath)
    
    return {
        'success': success,
        'filepath': filepath if success else None,
        'type': media_type
    }

async def main():
    # Example 1: Download with pin ID
    result = await download_pinterest(
        pin_id="980166306379767499",
        save_location="downloads"
    )
    print(f"Result: {result}\n")
    
    # Example 2: Download with full URL and custom filename
    result = await download_pinterest(
        pin_id="https://www.pinterest.com/pin/980166306379767499/",
        save_location="downloads",
        filename="my_cat_pic"
    )
    print(f"Result: {result}\n")
    
    # Example 3: Download multiple pins
    pin_ids = ["980166306379767499", "123456789012345678"]
    for pin_id in pin_ids:
        result = await download_pinterest(
            pin_id=pin_id,
            save_location="downloads/batch"
        )
        print(f"Downloaded: {result['filepath']}\n")

if __name__ == "__main__":
    asyncio.run(main())