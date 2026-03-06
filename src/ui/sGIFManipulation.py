from PIL import Image, ImageSequence
import io
import asyncio

def CompressGIF(input_path, output_path, scale=0.5, optimize=True, colors=128):
    img = Image.open(input_path)
    
    frames = []
    for frame in ImageSequence.Iterator(img):
        frame = frame.convert("P", palette=Image.ADAPTIVE, colors=colors)
        if scale != 1:
            new_size = (int(frame.width * scale), int(frame.height * scale))
            frame = frame.resize(new_size, Image.LANCZOS)
        frames.append(frame)

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        optimize=optimize,
        loop=img.info.get("loop", 0),
        duration=img.info.get("duration", 100)
    )
    print(f"Compressed GIF saved to {output_path}")

async def ExtractLastFrame(gif_path: str) -> tuple[io.BytesIO, float]:
    total_duration_ms = 0

    with Image.open(gif_path) as img:
        frame_index = 0

        try:
            while True:
                img.seek(frame_index)
                total_duration_ms += img.info.get("duration", 0)

                frame_index += 1
        except EOFError:
            pass
        frame = img.convert("RGBA")

        buffer = io.BytesIO()
        frame.save(buffer, format="PNG")
        buffer.seek(0)

    total_duration_seconds = total_duration_ms / 1000.0

    return buffer, total_duration_seconds

if __name__ == "__main__":
    input_gif = "Animated.gif"  
    output_gif = "Animated1.gif"
    #CompressGIF(input_gif, output_gif, scale=0.7, colors=128)