function get_url () {
  // 如果有缓存记录
  let hostUrl = localStorage.getItem('_hostUrl') || ''
  if (hostUrl) {
    return hostUrl
  }
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`
  return url
}

function getFilenameAndCategoryFromUrl (url) {
  const queryString = url.split('?')[1]
  if (!queryString) {
    return {}
  }

  const params = new URLSearchParams(queryString)

  const filename = params.get('filename')
    ? decodeURIComponent(params.get('filename'))
    : null
  const category = params.get('category')
    ? decodeURIComponent(params.get('category') || '')
    : ''

  return { category, filename }
}

async function get_my_app (category = '', filename = null) {
  let url = get_url()
  const res = await fetch(`${url}/mixlab/workflow`, {
    method: 'POST',
    mode: 'cors', // 允许跨域请求
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      task: 'my_app',
      filename,
      category
    })
  })
  let result = await res.json()
  let data = []
  try {
    for (const res of result.data) {
      let { output, app } = res.data
      if (app.filename)
        data.push({
          ...app,
          data: output,
          date: res.date
        })
    }
  } catch (error) {}

  return data
}

async function getAppInit () {
  const { category, filename } = getFilenameAndCategoryFromUrl(
    window.location.href
  )
  return await get_my_app(category, filename)
}

function success (isSuccess, btn, text) {
  isSuccess ? (btn.innerText = 'success') : text
  setTimeout(() => {
    btn.innerText = text
  }, 5000)
}

async function interrupt () {
  try {
    await fetch(`${get_url()}/interrupt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: undefined
    })
  } catch (error) {
    console.error(error)
  }
  return true
}

async function getQueue (clientId) {
  try {
    const res = await fetch(`${get_url()}/queue`)
    const data = await res.json()
    return {
      // Running action uses a different endpoint for cancelling
      Running: Array.from(data.queue_running, prompt => {
        if (prompt[3].client_id === clientId) {
          let prompt_id = prompt[1]
          return {
            prompt_id,
            remove: () => interrupt()
          }
        }
      }),
      Pending: data.queue_pending.map(prompt => ({ prompt }))
    }
  } catch (error) {
    console.error(error)
    return { Running: [], Pending: [] }
  }
}

// 请求历史数据
async function getPromptResult (category) {
  let url = get_url()
  try {
    const response = await fetch(`${url}/mixlab/prompt_result`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        action: 'all'
      })
    })

    if (response.ok) {
      const data = await response.json()
      console.log('#getPromptResult:', category, data)

      return data.result.filter(r => r.appInfo.category == category)
      // 处理返回的数据
    } else {
      console.log('Error:', response.status)
      // 处理错误情况
    }
  } catch (error) {
    console.log('Error:', error)
    // 处理异常情况
  }
}

// 新的运行工作流的接口
function queuePromptNew (filename, category, seed, input, client_id) {
  let url = get_url()
  // var filename = "Text-to-Image_1.json", category = "";

  // 随机seed
  //  promptWorkflow = randomSeed(seed, promptWorkflow);
  let d = { filename, category, seed, input, client_id }
  if (apps) {
    d.apps = apps
  }

  const data = JSON.stringify(d)
  return new Promise((res, rej) => {
    fetch(`${url}/mixlab/prompt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: data
    })
      .then(response => {
        if (!response.ok) {
          // Handle HTTP error responses
          if (response.status === 400) {
            return response.json().then(errorData => {
              // Process the error data
              console.error('Error 400:', errorData)
              alert(JSON.stringify(errorData, null, 2))
              res(null)
            })
          }
          throw new Error('Network response was not ok')
        }
        return response.json() // Process the response data
      })
      .then(data => {
        // Handle the response data
        console.log('Success:', data)
        res(true)
      })
      .catch(error => {
        // Handle fetch errors
        console.error('Fetch error:', error)
        res(null)
      })
  })
}

// 保存历史数据
async function savePromptResult (data) {
  let url = get_url()
  try {
    const response = await fetch(`${url}/mixlab/prompt_result`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        action: 'save',
        data
      })
    })

    if (response.ok) {
      const res = await response.json()
      console.log('Response:', res)
      return res
      // 处理返回的数据
    } else {
      console.log('Error:', response.status)
      // 处理错误情况
    }
  } catch (error) {
    console.log('Error:', error)
    // 处理异常情况
  }
}

async function uploadImage (blob, fileType = '.png', filename) {
  const body = new FormData()
  body.append(
    'image',
    new File([blob], (filename || new Date().getTime()) + fileType)
  )

  const url = get_url()

  const resp = await fetch(`${url}/upload/image`, {
    method: 'POST',
    body
  })

  let data = await resp.json()
  // console.log(data)
  let { name, subfolder } = data
  let src = `${url}/view?filename=${encodeURIComponent(
    name
  )}&type=input&subfolder=${subfolder}&rand=${Math.random()}`

  return { url: src, name }
}

async function uploadMask (arrayBuffer, imgurl) {
  const body = new FormData()
  const filename = 'clipspace-mask-' + performance.now() + '.png'

  let original_url = new URL(imgurl)

  const original_ref = { filename: original_url.searchParams.get('filename') }

  let original_subfolder = original_url.searchParams.get('subfolder')
  if (original_subfolder) original_ref.subfolder = original_subfolder

  let original_type = original_url.searchParams.get('type')
  if (original_type) original_ref.type = original_type

  body.append('image', arrayBuffer, filename)
  body.append('original_ref', JSON.stringify(original_ref))
  body.append('type', 'input')
  body.append('subfolder', 'clipspace')

  const url = get_url()

  const resp = await fetch(`${url}/upload/mask`, {
    method: 'POST',
    body
  })

  // console.log(resp)
  let data = await resp.json()
  let { name, subfolder, type } = data
  let src = `${url}/view?filename=${encodeURIComponent(
    name
  )}&type=${type}&subfolder=${subfolder}&rand=${Math.random()}`

  return { url: src, name: 'clipspace/' + name }
}

const parseImageToBase64 = url => {
  return new Promise((res, rej) => {
    fetch(url)
      .then(response => response.blob())
      .then(blob => {
        const reader = new FileReader()
        reader.onloadend = () => {
          const base64data = reader.result
          res(base64data)
          // 在这里可以将base64数据用于进一步处理或显示图片
        }
        reader.readAsDataURL(blob)
      })
      .catch(error => {
        console.log('发生错误:', error)
      })
  })
}

function createImage (url) {
  let im = new Image()
  return new Promise((res, rej) => {
    im.onload = () => res(im)
    im.src = url
  })
}

function convertImageToBlackBasedOnAlpha (image) {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')

  // Draw the image onto the canvas
  canvas.width = image.width
  canvas.height = image.height
  ctx.drawImage(image, 0, 0)

  // Get the image data from the canvas
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
  const pixels = imageData.data

  // Modify the RGB values based on the alpha channel
  for (let i = 0; i < pixels.length; i += 4) {
    const alpha = pixels[i + 3]
    if (alpha !== 0) {
      // Set non-transparent pixels to black
      pixels[i] = 0 // Red
      pixels[i + 1] = 0 // Green
      pixels[i + 2] = 0 // Blue
    }
  }

  // Put the modified image data back onto the canvas
  ctx.putImageData(imageData, 0, 0)

  // Convert the modified canvas to base64 data URL
  const base64ImageData = canvas.toDataURL('image/png') // Replace 'png' with your desired image format

  return base64ImageData
}

const blobToBase64 = blob => {
  return new Promise((res, rej) => {
    const reader = new FileReader()
    reader.onloadend = () => {
      const base64data = reader.result
      res(base64data)
      // 在这里可以将base64数据用于进一步处理或显示图片
    }
    reader.readAsDataURL(blob)
  })
}

function base64ToBlob (base64) {
  // 去除base64编码中的前缀
  const base64WithoutPrefix = base64.replace(/^data:image\/\w+;base64,/, '')

  // 将base64编码转换为字节数组
  const byteCharacters = atob(base64WithoutPrefix)

  // 创建一个存储字节数组的数组
  const byteArrays = []

  // 将字节数组放入数组中
  for (let offset = 0; offset < byteCharacters.length; offset += 1024) {
    const slice = byteCharacters.slice(offset, offset + 1024)

    const byteNumbers = new Array(slice.length)
    for (let i = 0; i < slice.length; i++) {
      byteNumbers[i] = slice.charCodeAt(i)
    }

    const byteArray = new Uint8Array(byteNumbers)
    byteArrays.push(byteArray)
  }

  // 创建blob对象
  const blob = new Blob(byteArrays, { type: 'image/png' }) // 根据实际情况设置MIME类型

  return blob
}

async function calculateImageHash (blob) {
  const buffer = await blob.arrayBuffer()
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const hashHex = hashArray
    .map(byte => byte.toString(16).padStart(2, '0'))
    .join('')
  return hashHex
}

// 获取 rembg 模型
async function get_rembg_models () {
  try {
    const response = await fetch(`${get_url()}/mixlab/folder_paths`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        type: 'rembg'
      })
    })

    const data = await response.json()
    // console.log(data)
    return data.names
  } catch (error) {
    console.error(error)
  }
}

//自动抠图
async function run_rembg (model, base64) {
  try {
    const response = await fetch(`${get_url()}/mixlab/rembg`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model,
        base64
      })
    })

    const data = await response.json()
    // console.log(data)
    return data.data
  } catch (error) {
    console.error(error)
  }
}

function copyHtmlWithImagesToClipboard (data, cb) {
  // 创建一个临时div元素
  const tempDiv = document.createElement('div')

  // 将HTML字符串赋值给div的innerHTML属性
  tempDiv.innerHTML = data

  // 获取div中的所有图像元素
  const images = tempDiv.getElementsByTagName('img')

  // 遍历图像元素，并将图像数据转换为Base64编码
  for (let i = 0; i < images.length; i++) {
    const image = images[i]
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')

    // 设置canvas尺寸与图像尺寸相同
    canvas.width = image.width
    canvas.height = image.height

    // 在canvas上绘制图像
    context.drawImage(image, 0, 0)

    // 将canvas转换为Base64编码
    const imageData = canvas.toDataURL()

    // 将Base64编码替换图像元素的src属性
    image.src = imageData
  }

  let richText = tempDiv.innerHTML

  // 创建一个新的Blob对象，并将富文本字符串作为数据传递进去
  const blob = new Blob([richText], { type: 'text/html' })

  // 创建一个ClipboardItem对象，并将Blob对象添加到其中
  const clipboardItem = new ClipboardItem({ 'text/html': blob })

  // 使用Clipboard API将内容复制到剪贴板
  navigator.clipboard
    .write([clipboardItem])
    .then(() => {
      console.log('富文本已成功复制到剪贴板')
      tempDiv.remove()
      if (cb) cb(true)
    })
    .catch(error => {
      console.error('复制到剪贴板失败:', error)
      tempDiv.remove()
      if (cb) cb(false)
    })
}

function copyImagesToClipboard (html, cb) {
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = html
  const images = tempDiv.querySelectorAll('img')
  const promises = Array.from(images).map(image => {
    return new Promise(resolve => {
      const img = new Image()
      img.src = image.src
      img.onload = () => {
        const canvas = document.createElement('canvas')
        const context = canvas.getContext('2d')
        canvas.width = img.width
        canvas.height = img.height
        context.drawImage(img, 0, 0)
        canvas.toBlob(blob => {
          const clipboardItem = new ClipboardItem({ 'image/png': blob })
          navigator.clipboard
            .write([clipboardItem])
            .then(() => {
              resolve()
              tempDiv.remove()
              if (cb) cb(true)
            })
            .catch(error => {
              reject(error)
              tempDiv.remove()
              if (cb) cb(false)
            })
        })
      }
    })
  })
  Promise.all([...promises])
    .then(() => {
      console.log('所有图片已成功复制到剪贴板')
      if (cb) cb(true)
      tempDiv.remove()
    })
    .catch(error => {
      console.error('复制到剪贴板失败:', error)
      if (cb) cb(false)
      tempDiv.remove()
    })
}

function copyTextToClipboard (html, cb) {
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = html

  const text = tempDiv.innerText
  const textData = new ClipboardItem({
    'text/plain': new Blob([text], { type: 'text/plain' })
  })

  navigator.clipboard
    .write([textData])
    .then(() => {
      console.log('所有文本已成功复制到剪贴板', text)
      if (cb) cb(true)
      tempDiv.remove()
    })
    .catch(error => {
      console.error('复制到剪贴板失败:', error)
      if (cb) cb(false)
      tempDiv.remove()
    })
}

// ComfyUI\web\extensions\core\dynamicPrompts.js
// 官方实现修改
// Allows for simple dynamic prompt replacement
// Inputs in the format {a|b} will have a random value of a or b chosen when the prompt is queued.

/*
 * Strips C-style line and block comments from a string
 */
function dynamicPrompts (prompt) {
  prompt = prompt.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  while (
    prompt.replace('\\{', '').includes('{') &&
    prompt.replace('\\}', '').includes('}')
  ) {
    const startIndex = prompt.replace('\\{', '00').indexOf('{')
    const endIndex = prompt.replace('\\}', '00').indexOf('}')

    const optionsString = prompt.substring(startIndex + 1, endIndex)
    const options = optionsString.split('|')

    const randomIndex = Math.floor(Math.random() * options.length)
    const randomOption = options[randomIndex]

    prompt =
      prompt.substring(0, startIndex) +
      randomOption +
      prompt.substring(endIndex + 1)
  }
  return prompt
}

// 遍历所有组合,语法同 动态提示
function generateAllCombinations (prompt) {
  prompt = prompt.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')

  // Helper function to get all combinations
  function getAllCombinations (parts) {
    if (parts.length === 0) return ['']
    const [firstPart, ...restParts] = parts
    const restCombinations = getAllCombinations(restParts)
    const allCombinations = []

    firstPart.forEach(option => {
      restCombinations.forEach(combination => {
        allCombinations.push(option + combination)
      })
    })

    return allCombinations
  }

  // Split prompt into static parts and dynamic parts
  let parts = []
  let startIndex = 0

  while (
    prompt.replace('\\{', '').includes('{') &&
    prompt.replace('\\}', '').includes('}')
  ) {
    startIndex = prompt.replace('\\{', '00').indexOf('{')
    const endIndex = prompt.replace('\\}', '00').indexOf('}')
    const staticPart = prompt.substring(0, startIndex)
    const optionsString = prompt.substring(startIndex + 1, endIndex)
    const options = optionsString.split('|')

    parts.push([staticPart])
    parts.push(options)

    prompt = prompt.substring(endIndex + 1)
  }

  // Add the remaining static part
  parts.push([prompt])

  // Get all combinations
  const combinations = getAllCombinations(parts)

  return combinations
}

const _textNodes = [
    'TextInput_',
    'CLIPTextEncode',
    'PromptSimplification',
    'ChinesePrompt_Mix'
  ],
  _loraNodes = ['CheckpointLoaderSimple', 'LoraLoader'],
  _numberNodes = ['FloatSlider', 'IntNumber'],
  _slideNodes = ['PromptSlide'],
  _imageNodes = [
    'LoadImage',
    'VHS_LoadVideo',
    'ImagesPrompt_',
    'LoadImagesToBatch'
  ],
  _colorNodes = ['Color'],
  _audioNodes = ['LoadAndCombinedAudio_']

export default {
  get_url,
  get_my_app,
  getAppInit,
  getFilenameAndCategoryFromUrl,
  success,
  interrupt,
  getQueue,
  queuePromptNew,
  savePromptResult,
  uploadImage,
  uploadMask,
  run_rembg,
  get_rembg_models,
  parseImageToBase64,
  createImage,
  convertImageToBlackBasedOnAlpha,
  blobToBase64,
  base64ToBlob,
  calculateImageHash,
  copyHtmlWithImagesToClipboard,
  copyImagesToClipboard,
  copyTextToClipboard,
  dynamicPrompts,
  generateAllCombinations,

  _textNodes,
  _loraNodes,
  _numberNodes,
  _slideNodes,
  _imageNodes,
  _colorNodes,
  _audioNodes
}
