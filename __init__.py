#
import os
import subprocess
import importlib.util
import sys

python = sys.executable


from server import PromptServer
try:
    import aiohttp
    from aiohttp import web
except ImportError:
    print("Module 'aiohttp' not installed. Please install it via:")
    print("pip install aiohttp")
    print("or")
    print("pip install -r requirements.txt")
    sys.exit()



def create_key(key_p,crt_p):
    import OpenSSL
    # 生成自签名证书
    # 生成私钥
    private_key = OpenSSL.crypto.PKey()
    private_key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)

    # 生成CSR
    csr = OpenSSL.crypto.X509Req()
    csr.get_subject().CN = "mixlab.com"  # 设置证书的通用名称
    csr.set_pubkey(private_key)
    csr.sign(private_key, "sha256")
    # 生成证书
    certificate = OpenSSL.crypto.X509()
    certificate.set_serial_number(1)
    certificate.gmtime_adj_notBefore(0)
    certificate.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # 设置证书的有效期
    certificate.set_issuer(csr.get_subject())
    certificate.set_subject(csr.get_subject())
    certificate.set_pubkey(csr.get_pubkey())
    certificate.sign(private_key, "sha256")
    # 保存私钥到文件
    with open(key_p, "wb") as f:
        f.write(OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, private_key))

    # 保存证书到文件
    with open(crt_p, "wb") as f:
        f.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, certificate))
    return

def create_for_https():
    current_path = os.path.abspath(os.path.dirname(__file__))
    # print("#####path::", current_path)

    # TODO 处理路径
    https_key_path=os.path.join(current_path, "https")
    crt=os.path.join(https_key_path, "certificate.crt")
    key=os.path.join(https_key_path, "private.key")
    print("##https_key_path", crt,key)
    if not os.path.exists(https_key_path):
        # 使用mkdir()方法创建新目录
        os.mkdir(https_key_path)
    if not os.path.exists(crt):
        create_key(key,crt)
    return (crt,key)


# https
async def new_start(self, address, port, verbose=True, call_on_start=None):
        runner = web.AppRunner(self.app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, address, port)
        await site.start()

        import ssl
        crt,key=create_for_https()
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(crt,key)
        site2 = web.TCPSite(runner, address, port+1,ssl_context=ssl_context)
        await site2.start()

        if address == '':
            address = '0.0.0.0'
        if verbose:
            print("Starting server\n")
            print("To see the GUI go to: http://{}:{}".format(address, port))
            print("To see the GUI go to: https://{}:{}".format(address, port+1))
        if call_on_start is not None:
            call_on_start(address, port)

        # import webbrowser
        # if os.name == 'nt' and address == '0.0.0.0':
        #     address = '127.0.0.1'
        # webbrowser.open(f"https://{address}")
        # webbrowser.open(f"http://{address}:{port}")


PromptServer.start=new_start


def is_installed(package, package_overwrite=None):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        pass

    package = package_overwrite or package

    if spec is None:
        print(f"Installing {package}...")
        # 清华源 -i https://pypi.tuna.tsinghua.edu.cn/simple
        command = f'"{python}" -m pip install {package}'
  
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ)

        if result.returncode != 0:
            print(f"Couldn't install\nCommand: {command}\nError code: {result.returncode}")

is_installed('pyOpenSSL')

# 扩展api接口
# from server import PromptServer
# from aiohttp import web

# @routes.post('/ws_image')
# async def my_hander_method(request):
#     post = await request.post()
#     x = post.get("something")
#     return web.json_response({})


# 导入节点
from .nodes.PromptNode import RandomPrompt
from .nodes.ImageNode import TransparentImage,LoadImagesFromPath,AreaToMask,SmoothMask,FeatheredMask,SplitLongMask,ImageCropByAlpha,EnhanceImage,FaceToMask
from .nodes.Vae import VAELoader,VAEDecode
from .nodes.ScreenShareNode import ScreenShareNode,FloatingVideo
from .nodes.Clipseg import CLIPSeg,CombineMasks

# 要导出的所有节点及其名称的字典
# 注意：名称应全局唯一
NODE_CLASS_MAPPINGS = {
    "RandomPrompt":RandomPrompt,
    "TransparentImage":TransparentImage,
    "LoadImagesFromPath":LoadImagesFromPath,
    "EnhanceImage":EnhanceImage,
    "SplitLongMask":SplitLongMask,
    "FeatheredMask":FeatheredMask,
    "SmoothMask":SmoothMask,
    "FaceToMask":FaceToMask,
    "AreaToMask":AreaToMask,
    "ImageCropByAlpha":ImageCropByAlpha,
    "VAELoaderConsistencyDecoder":VAELoader,
    "VAEDecodeConsistencyDecoder":VAEDecode,
    "ScreenShare":ScreenShareNode,
    "FloatingVideo":FloatingVideo,
    "CLIPSeg":CLIPSeg,
    "CombineMasks":CombineMasks
}

# 一个包含节点友好/可读的标题的字典
NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomPrompt": "Random Prompt #Example Node",
    "SplitLongMask":"Splitting a long image into sections",
    "VAELoaderConsistencyDecoder":"Consistency Decoder Loader",
    "VAEDecodeConsistencyDecoder":"Consistency Decoder Decode"
}

# web ui的节点功能
WEB_DIRECTORY = "./web"

print('--------------')
print('\033[34mMixlab Custom Nodes: \033[92mLoaded\033[0m')
print('--------------')