'\nTTS 工具：使用 edge-tts 在线文本转语音（微软 Edge 引擎，免费无需 API Key）\n音质与 https://www.text-to-speech.cn/ 类似（均基于微软 TTS）\n'
import os
OPENAGI_TTS_VOICE=os.getenv('OPENAGI_TTS_VOICE','zh-CN-XiaoxiaoNeural')
OPENAGI_TTS_RATE=os.getenv('OPENAGI_TTS_RATE','+25%')
async def text_to_speech_async(text:str):
	'\n    将文本转为 MP3 音频字节（异步）。\n    @param text 待朗读文本（会被截断到 600 字符）\n    @returns (音频字节, media_type) 如 (mp3_bytes, "audio/mpeg")\n    @raises Exception edge-tts 调用失败\n    ';A=text;import edge_tts as E;A=(A or'').strip()[:600]
	if not A:raise ValueError('text 不能为空')
	F=OPENAGI_TTS_VOICE;G=OPENAGI_TTS_RATE;H=E.Communicate(A,F,rate=G);B=[]
	async for C in H.stream():
		if C['type']=='audio':B.append(C['data'])
	D=b''.join(B)
	if not D:raise RuntimeError('edge-tts 未返回音频')
	return D,'audio/mpeg'