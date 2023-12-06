import { app } from '../../../scripts/app.js'
// import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

let api_host = `${window.location.hostname}:${window.location.port}`
let api_base = ''
let url = `${window.location.protocol}//${api_host}${api_base}`

async function getQueue () {
  try {
    const res = await fetch(`${url}/queue`)
    const data = await res.json()
    // console.log(data.queue_running,data.queue_pending)
    return {
      // Running action uses a different endpoint for cancelling
      Running: data.queue_running.length,
      Pending: data.queue_pending.length
    }
  } catch (error) {
    console.error(error)
    return { Running: 0, Pending: 0 }
  }
}

async function interrupt () {
  const resp = await fetch(`${url}/interrupt`, {
    method: 'POST'
  })
}

async function clipboardWriteImage (win, url) {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  // console.log(url)
  const img = await createImage(url)
  // console.log(img)
  canvas.width = img.naturalWidth
  canvas.height = img.naturalHeight

  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(img, 0, 0)
  // 将canvas转为blob
  canvas.toBlob(async blob => {
    const data = [
      new ClipboardItem({
        [blob.type]: blob
      })
    ]

    win.navigator.clipboard
      .write(data)
      .then(() => {
        console.log('Image copied to clipboard')
      })
      .catch(error => {
        console.error('Failed to copy image to clipboard:', error)
      })
  })
}

async function uploadFile (file) {
  try {
    const body = new FormData()
    body.append('image', file)
    body.append('overwrite', 'true')
    body.append('type', 'temp')

    const resp = await fetch(`${url}/upload/image`, {
      method: 'POST',
      body
    })

    if (resp.status === 200) {
      const data = await resp.json()
      let path = data.name
      if (data.subfolder) path = data.subfolder + '/' + path
      return path
    } else {
      alert(resp.status + ' - ' + resp.statusText)
    }
  } catch (error) {
    alert(error)
  }
}

// function switchCamera (deviceId = 'desktop') {
//   const constraints = {
//     audio: false,
//     video: {
//       width: { ideal: 1920, max: 1920 },
//       height: { ideal: 1080, max: 1080 },
//       deviceId: mediaDevices[webcamsEl.value].deviceId
//     }
//   }
//   console.log('switchCamera', constraints)

//   let mediaStreamPro
//   if (deviceId === 'desktop') {
//     mediaStreamPro = navigator.mediaDevices.getDisplayMedia(constraints)
//   } else {
//     mediaStreamPro = navigator.mediaDevices.getUserMedia(constraints)
//   }
//   return mediaStreamPro
// }

// alert(navigator.mediaDevices)

async function shareScreen (
  isCamera = false,
  webcamVideo,
  shareBtn,
  liveBtn,
  previewArea
) {
  try {
    let mediaStream

    if (!isCamera) {
      mediaStream = await navigator.mediaDevices.getDisplayMedia({
        video: true
      })
    } else {
      if (!localStorage.getItem('_mixlab_webcamera_select')) return
      let constraints =
        JSON.parse(localStorage.getItem('_mixlab_webcamera_select')) || {}
      mediaStream = await navigator.mediaDevices.getUserMedia(constraints)
    }

    webcamVideo.removeEventListener('timeupdate', videoTimeUpdateHandler)
    webcamVideo.srcObject = mediaStream
    webcamVideo.onloadedmetadata = () => {
      let x = 0,
        y = 0,
        width = webcamVideo.videoWidth,
        height = webcamVideo.videoHeight,
        imgWidth = webcamVideo.videoWidth,
        imgHeight = webcamVideo.videoHeight

      let d = getSetAreaData()
      if (
        d &&
        d.x >= 0 &&
        d.imgWidth === imgWidth &&
        d.imgHeight === imgHeight
      ) {
        x = d.x
        y = d.y
        width = d.width
        height = d.height
        imgWidth = d.imgWidth
        imgHeight = d.imgHeight
        console.log('#screen_share::使用上一次选区')
      }
      updateSetAreaData(x, y, width, height, imgWidth, imgHeight)

      webcamVideo.play()

      createBlobFromVideo(webcamVideo, true)

      webcamVideo.addEventListener('timeupdate', videoTimeUpdateHandler)

      // window._mixlab_screen_x = 0
      // window._mixlab_screen_y = 0
      // // console.log(webcamVideo)
      // window._mixlab_screen_width = webcamVideo.videoWidth
      // window._mixlab_screen_height = webcamVideo.videoHeight
    }

    mediaStream.addEventListener('inactive', handleStopSharing)

    // 停止共享的回调函数
    function handleStopSharing () {
      // console.log('用户停止了共享')
      // 执行其他操作
      if (window._mixlab_stopVideo) {
        window._mixlab_stopVideo()
        window._mixlab_stopVideo = null
        shareBtn.innerText = 'Share Screen'
      }
      if (window._mixlab_stopLive) {
        window._mixlab_stopLive()
        window._mixlab_stopLive = null
        liveBtn.innerText = 'Live Run'
      }
      return
    }

    window._mixlab_screen_webcamVideo = webcamVideo

    async function videoTimeUpdateHandler () {
      if (!window._mixlab_screen_live) return
      createBlobFromVideo(webcamVideo)
    }
  } catch (error) {
    alert('Error accessing screen stream: ' + error)
  }
  return () => {
    webcamVideo.pause() // 暂停视频播放
    webcamVideo.srcObject.getTracks().forEach(track => {
      track.stop()
    })
    webcamVideo.srcObject = null // 清空视频源对象
    window._mixlab_screen_live = false
    window._mixlab_screen_blob = null
    previewArea.innerHTML = ''
    interrupt()
  }
}

async function sleep (t = 200) {
  return new Promise((res, rej) => {
    setTimeout(() => {
      res(true)
    }, t)
  })
}

function createImage (url) {
  let im = new Image()
  return new Promise((res, rej) => {
    im.onload = () => res(im)
    im.src = url
  })
}

async function compareImages (threshold, previousImage, currentImage) {
  // 将 base64 转换为 Image 对象
  var previousImg = await createImage(previousImage)
  var currentImg = await createImage(currentImage)

  if (
    previousImg.naturalWidth != currentImg.naturalWidth ||
    previousImg.naturalHeight != currentImg.naturalHeight
  ) {
    return true // 图片有变化
  }

  // 创建一个 canvas 元素
  var canvas1 = document.createElement('canvas')
  canvas1.width = previousImg.naturalWidth
  canvas1.height = previousImg.naturalHeight
  var context1 = canvas1.getContext('2d')

  // 将图片绘制到 canvas 上
  context1.drawImage(previousImg, 0, 0)

  // 获取图片的像素数据
  var previousData = context1.getImageData(
    0,
    0,
    previousImg.naturalWidth,
    previousImg.naturalHeight
  ).data

  var canvas2 = document.createElement('canvas')
  canvas2.width = currentImg.naturalWidth
  canvas2.height = currentImg.naturalHeight
  var context2 = canvas2.getContext('2d')
  context2.drawImage(currentImg, 0, 0)
  var currentData = context2.getImageData(
    0,
    0,
    currentImg.naturalWidth,
    currentImg.naturalHeight
  ).data

  // 遍历每个像素点，计算像素差异
  var pixelDiff = 0
  for (var i = 0; i < previousData.length; i += 4) {
    var diffR = Math.abs(previousData[i] - currentData[i])
    var diffG = Math.abs(previousData[i + 1] - currentData[i + 1])
    var diffB = Math.abs(previousData[i + 2] - currentData[i + 2])

    // 计算像素差异总和
    pixelDiff += diffR + diffG + diffB
  }

  // 计算平均像素差异
  var averageDiff = pixelDiff / (previousData.length / 4)

  // 判断平均像素差异是否超过阈值
  // console.log(
  //   pixelDiff,
  //   averageDiff,
  //   threshold,
  //   currentImg.naturalWidth,
  //   currentImg.naturalHeight,previousData,currentData
  // )
  if (averageDiff > threshold) {
    return true // 图片有变化
  } else {
    return false // 图片无变化
  }
}

async function startLive (btn) {
  if (btn) window._mixlab_screen_live = !window._mixlab_screen_live

  if (btn) btn.innerText = `Stop Live`
  // console.log('#ML', 'live run', window._mixlab_screen_time)
  // if (window._mixlab_screen_time) {
  //   // console.log('#ML', 'live')
  //   return
  // }
  const { Pending, Running } = await getQueue()
  // console.log('#ML', Pending, window._mixlab_screen_blob)
  if (Pending <= 1 && window._mixlab_screen_blob && Running === 0) {
    // window._mixlab_screen_time = true

    const threshold = 1 // 阈值
    const previousImage = window._mixlab_screen_imagePath // 上一张图片的 base64
    let currentImage = await blobToBase64(window._mixlab_screen_blob)

    if (previousImage) {
      // 现在新的图片的 base64
      const imageChanged = await compareImages(
        threshold,
        previousImage,
        currentImage
      )
      console.log('#图片是否有变化:', imageChanged)

      if (imageChanged) {
        window._mixlab_screen_imagePath = currentImage
        document.querySelector('#queue-button').click()
      }
    } else {
      window._mixlab_screen_imagePath = currentImage
      // console.log(window._mixlab_screen_imagePath)
      document.querySelector('#queue-button').click()
    }

    // await uploadFile(file)
    // window._mixlab_screen_time = false

    await sleep(window._mixlab_screen_refresh_rate || 200)
    // console.log('#ML', window._mixlab_screen_imagePath)
  }

  if (btn) {
    startLive()
    return () => {
      // stop
      window._mixlab_screen_live = false
      window._mixlab_screen_blob = null
      interrupt()
    }
  } else if (window._mixlab_screen_live) {
    startLive()
  }
}

async function createBlobFromVideoForArea (webcamVideo) {
  const videoW = webcamVideo.videoWidth
  const videoH = webcamVideo.videoHeight
  const aspectRatio = videoW / videoH
  const WIDTH = videoW,
    HEIGHT = videoH
  const canvas = new OffscreenCanvas(WIDTH, HEIGHT)
  const ctx = canvas.getContext('2d')
  ctx.drawImage(webcamVideo, 0, 0, videoW, videoH, 0, 0, WIDTH, HEIGHT)

  const blob = await canvas.convertToBlob({
    type: 'image/jpeg',
    quality: 1
  })

  return blob
}

async function createBlobFromVideo (webcamVideo, updateImageBase64 = false) {
  const videoW = webcamVideo.videoWidth
  const videoH = webcamVideo.videoHeight
  const aspectRatio = videoW / videoH

  const { x, y, width, height } = window._mixlab_share_screen

  const canvas = new OffscreenCanvas(width, height)
  const ctx = canvas.getContext('2d')

  ctx.drawImage(webcamVideo, x, y, width, height, 0, 0, width, height)

  const blob = await canvas.convertToBlob({
    type: 'image/jpeg',
    quality: 1
  })
  // imgElement.src = await blobToBase64(blob)
  window._mixlab_screen_blob = blob

  console.log(
    '########updateImageBase64 ',
    updateImageBase64,
    x,
    y,
    width,
    height
  )
  if (updateImageBase64) {
    window._mixlab_screen_imagePath = await blobToBase64(blob)
  }
}

async function blobToBase64 (blob) {
  const reader = new FileReader()
  return new Promise((res, rej) => {
    reader.onload = function (event) {
      res(event.target.result)
    }
    reader.readAsDataURL(blob)
  })
}
function base64ToBlob (base64) {
  // 将Base64分割成类型和数据部分
  const parts = base64.split(';base64,')
  const type = parts[0].split(':')[1]
  const data = window.atob(parts[1])
  const arrayBuffer = new ArrayBuffer(data.length)
  const uint8Array = new Uint8Array(arrayBuffer)

  // 将Base64数据转换为Uint8Array
  for (let i = 0; i < data.length; i++) {
    uint8Array[i] = data.charCodeAt(i)
  }

  // 创建Blob对象
  const blob = new Blob([arrayBuffer], { type })

  return blob
}

async function requestCamera () {
  // 请求授权
  try {
    let stream = await navigator.mediaDevices.getUserMedia({ video: true })
    console.log('摄像头授权成功')
    // 获取视频轨道
    var videoTrack = stream.getVideoTracks()[0]

    // 停止视频轨道
    videoTrack.stop()

    return true
  } catch (error) {
    // 用户拒绝授权或发生其他错误
    console.error('摄像头授权失败：', error)

    // 提示用户授权摄像头访问权限
    if (error.name === 'NotAllowedError') {
      alert('请授权摄像头访问权限 chrome://settings/content/camera')
    } else {
      alert('摄像头访问权限请求失败，请重试 chrome://settings/content/camera')
    }

    // // 跳转到浏览器的授权设置页面
    // window.location.href = 'chrome://settings/content/camera'
  }
  return false
}

/* 
A method that returns the required style for the html 
*/
function get_position_style (ctx, widget_width, y, node_height) {
  const MARGIN = 4 // the margin around the html element

  /* Create a transform that deals with all the scrolling and zooming */
  const elRect = ctx.canvas.getBoundingClientRect()
  const transform = new DOMMatrix()
    .scaleSelf(
      elRect.width / ctx.canvas.width,
      elRect.height / ctx.canvas.height
    )
    .multiplySelf(ctx.getTransform())
    .translateSelf(MARGIN, MARGIN + y)

  return {
    transformOrigin: '0 0',
    transform: transform,
    left: `0`,
    top: `0`,
    cursor: 'pointer',
    position: 'absolute',
    maxWidth: `${widget_width - MARGIN * 2}px`,
    // maxHeight: `${node_height - MARGIN * 2}px`, // we're assuming we have the whole height of the node
    width: `${widget_width - MARGIN * 2}px`,
    // height: `${node_height - MARGIN * 2}px`,
    background: '#EEEEEE',
    display: 'flex',
    flexDirection: 'column',
    // alignItems: 'center',
    justifyContent: 'space-around'
  }
}

const base64Df =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAAAXNSR0IArs4c6QAAALZJREFUKFOFkLERwjAQBPdbgBkInECGaMLUQDsE0AkRVRAYWqAByxldPPOWHwnw4OBGye1p50UDSoA+W2ABLPN7i+C5dyC6R/uiAUXRQCs0bXoNIu4QPQzAxDKxHoALOrZcqtiyR/T6CXw7+3IGHhkYcy6BOR2izwT8LptG8rbMiCRAUb+CQ6WzQVb0SNOi5Z2/nX35DRyb/ENazhpWKoGwrpD6nICp5c2qogc4of+c7QcrhgF4Aa/aoAFHiL+RAAAAAElFTkSuQmCC'

app.registerExtension({
  name: 'Mixlab.image.ScreenShareNode',
  async getCustomWidgets (app) {
    // console.log('#Mixlab.image.ScreenShareNode', app)
    return {
      CHEESE (node, inputName, inputData, app) {
        // We return an object containing a field CHEESE which has a function (taking node, name, data, app)
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 12], // a default size
          draw (ctx, node, width, y) {
            // a method to draw the widget (ctx is a CanvasRenderingContext2D)
          },
          computeSize (...args) {
            return [128, 12] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            return window._mixlab_screen_imagePath || base64Df
          }
        }
        // console.log('#Mixlab.image.ScreenShareNode',widget)
        node.addCustomWidget(widget)
        return widget // and returns it.
      },
      PROMPT (node, inputName, inputData, app) {
        // We return an object containing a field CHEESE which has a function (taking node, name, data, app)
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 12], // a default size
          draw (ctx, node, width, y) {
            // a method to draw the widget (ctx is a CanvasRenderingContext2D)
          },
          computeSize (...args) {
            return [128, 12] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            return window._mixlab_screen_prompt || ''
          }
        }
        // console.log('###widget', widget)
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      },
      SLIDE (node, inputName, inputData, app) {
        // We return an object containing a field CHEESE which has a function (taking node, name, data, app)
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 12], // a default size
          draw (ctx, node, width, y) {
            // a method to draw the widget (ctx is a CanvasRenderingContext2D)
          },
          computeSize (...args) {
            return [128, 12] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            return window._mixlab_screen_slide_input || 0.5
          }
        }
        // console.log('###widget', widget)
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      },
      SEED (node, inputName, inputData, app) {
        // We return an object containing a field CHEESE which has a function (taking node, name, data, app)
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 12], // a default size
          draw (ctx, node, width, y) {
            // a method to draw the widget (ctx is a CanvasRenderingContext2D)
          },
          computeSize (...args) {
            return [128, 12] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            return window._mixlab_screen_seed_input || 0
          }
        }
        // console.log('###widget', widget)
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      }
    }
  },
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'ScreenShare') {
      /* 
          Hijack the onNodeCreated call to add our widget
          */
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)

        const widget = {
          type: 'HTML', // whatever
          name: 'sreen_share', // whatever
          draw (ctx, node, widget_width, y, widget_height) {
            console.log('ScreenSHare', y, widget_height)
            Object.assign(
              this.card.style,
              get_position_style(
                ctx,
                widget_width,
                widget_height * 5,
                node.size[1]
              )
            )
          }
        }

        widget.card = $el('div', {})

        widget.previewCard = $el('div', {})

        widget.preview = $el('video', {
          style: {
            width: '100%'
          },
          controls: true,
          poster:
            'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAAAXNSR0IArs4c6QAAALZJREFUKFOFkLERwjAQBPdbgBkInECGaMLUQDsE0AkRVRAYWqAByxldPPOWHwnw4OBGye1p50UDSoA+W2ABLPN7i+C5dyC6R/uiAUXRQCs0bXoNIu4QPQzAxDKxHoALOrZcqtiyR/T6CXw7+3IGHhkYcy6BOR2izwT8LptG8rbMiCRAUb+CQ6WzQVb0SNOi5Z2/nX35DRyb/ENazhpWKoGwrpD6nICp5c2qogc4of+c7QcrhgF4Aa/aoAFHiL+RAAAAAElFTkSuQmCC'
        })

        widget.previewArea = $el('div', {
          style: {}
        })

        widget.shareDiv = $el('div', {
          // innerText: 'Share Screen',
          style: {
            cursor: 'pointer',
            fontWeight: '300',
            display: 'flex'
          }
        })

        widget.shareBtn = $el('button', {
          innerText: 'Share Screen',
          style: {
            cursor: 'pointer',
            padding: '8px 0',
            fontWeight: '300',
            margin: '2px',
            width: '100%'
          }
        })

        widget.shareOfWebCamBtn = $el('button', {
          innerText: 'Camera',
          style: {
            cursor: 'pointer',
            padding: '8px 0',
            fontWeight: '300',
            margin: '2px',
            width: '100%'
          }
        })

        widget.openFloatingWinBtn = $el('button', {
          innerText: 'Set Area',
          style: {
            cursor: 'pointer',
            padding: '8px 0',
            fontWeight: '300',
            margin: '2px'
          }
        })

        widget.refreshInput = $el('input', {
          placeholder: '  Refresh rate:200 ms',
          type: 'number',
          min: 100,
          step: 100,
          style: {
            cursor: 'pointer',
            padding: '8px 0',
            fontWeight: '300',
            margin: '2px'
          }
        })
        widget.liveBtn = $el('button', {
          innerText: 'Live Run',
          style: {
            cursor: 'pointer',
            padding: '8px 0',
            fontWeight: '300',
            margin: '2px'
          }
        })

        document.body.appendChild(widget.card)

        widget.card.appendChild(widget.previewCard)
        widget.previewCard.appendChild(widget.preview)
        widget.previewCard.appendChild(widget.previewArea)

        widget.card.appendChild(widget.shareDiv)
        widget.shareDiv.appendChild(widget.shareBtn)
        widget.shareDiv.appendChild(widget.shareOfWebCamBtn)
        widget.card.appendChild(widget.openFloatingWinBtn)
        widget.card.appendChild(widget.refreshInput)
        widget.card.appendChild(widget.liveBtn)

        const toggleShare = async (isCamera = false) => {
          if (widget.preview.paused) {
            window._mixlab_stopVideo = await shareScreen(
              isCamera,
              widget.preview,
              widget.shareBtn,
              widget.liveBtn,
              widget.previewArea
            )

            if (isCamera) {
              widget.shareOfWebCamBtn.innerText = 'Stop Share'
              widget.shareBtn.innerText = 'Stop'
            } else {
              widget.shareOfWebCamBtn.innerText = 'Stop'
              widget.shareBtn.innerText = 'Stop Share'
            }

            console.log('视频已暂停')
            if (window._mixlab_stopLive) {
              window._mixlab_stopLive()
              window._mixlab_stopLive = null
              widget.liveBtn.innerText = 'Live Run'
            }

            setTimeout(() => updateSetAreaDisplay(), 2000)
          } else {
            console.log('视频正在播放')
            if (window._mixlab_stopVideo) {
              window._mixlab_stopVideo()
              window._mixlab_stopVideo = null
              widget.shareBtn.innerText = 'Share Screen'
              widget.shareOfWebCamBtn.innerText = 'Camera'
            }
            if (window._mixlab_stopLive) {
              window._mixlab_stopLive()
              window._mixlab_stopLive = null
              widget.liveBtn.innerText = 'Live Run'
            }
          }
        }

        // updateSetAreaDisplay(widget.previewArea, 200, 200)
        widget.shareOfWebCamBtn.addEventListener('click', async () => {
          if (!widget.preview.paused) {
            if (window._mixlab_stopVideo) {
              window._mixlab_stopVideo()
              window._mixlab_stopVideo = null
              widget.shareBtn.innerText = 'Share Screen'
              widget.shareOfWebCamBtn.innerText = 'Camera'
            }
            if (window._mixlab_stopLive) {
              window._mixlab_stopLive()
              window._mixlab_stopLive = null
              widget.liveBtn.innerText = 'Live Run'
            }
            return
          }

          let r = await requestCamera()
          if (r === false) return
          const devices = await navigator.mediaDevices.enumerateDevices()

          // 查找摄像头设备
          var cameras = devices.filter(function (device) {
            // console.log(device)
            return device.kind === 'videoinput'
          })

          // 创建 <select> 元素
          var select = document.createElement('select')

          // 创建默认选项
          // var defaultOption = document.createElement('option')
          // defaultOption.text = '请选择摄像头'
          // defaultOption.disabled = true
          // defaultOption.selected = true
          // select.appendChild(defaultOption)

          // 创建每个摄像头设备的选项
          Array.from(cameras, (camera, i) => {
            var option = document.createElement('option')
            option.value = camera.deviceId
            option.text = camera.label || 'Camera ' + (select.length - 1)
            if (i === 0) option.selected = true
            select.appendChild(option)
          })

          let modal = document.createElement('div')
          modal.className = 'comfy-modal'
          modal.style.display = 'flex'

          let modalContent = document.createElement('div')
          modalContent.className = 'comfy-modal-content'

          let title = document.createElement('p')
          title.innerText = 'Please select a camera'

          modalContent.appendChild(title)
          modalContent.appendChild(select)

          let btns = document.createElement('div')
          btns.style = `display: flex;
          justify-content: space-between;
          margin: 24px 0;`

          let btn = document.createElement('button')
          btn.innerText = 'OK'
          btn.style = `width: 112px;`

          let closeBtn = document.createElement('button')
          closeBtn.innerText = 'Cancel'
          closeBtn.style = `width: 112px;`

          modalContent.appendChild(btns)
          btns.appendChild(btn)
          btns.appendChild(closeBtn)

          modal.appendChild(modalContent)
          document.body.appendChild(modal)

          btn.addEventListener('click', () => {
            // 获取所选择的选项的索引
            var selectedIndex = select.selectedIndex

            // 获取所选择的选项的值
            var selectedValue = select.options[selectedIndex].value
            if (selectedValue) {
              const constraints = {
                audio: false,
                video: {
                  width: { ideal: 1920, max: 1920 },
                  height: { ideal: 1080, max: 1080 },
                  deviceId: selectedValue
                }
              }

              localStorage.setItem(
                '_mixlab_webcamera_select',
                JSON.stringify(constraints)
              )

              toggleShare(true)
            }

            modal.remove()
          })

          closeBtn.addEventListener('click', () => {
            modal.remove()
          })
        })

        widget.shareBtn.addEventListener('click', async () => {
          toggleShare()
        })

        widget.refreshInput.addEventListener('change', async () => {
          window._mixlab_screen_refresh_rate = Math.round(
            widget.refreshInput.value
          )
        })

        widget.liveBtn.addEventListener('click', async () => {
          if (window._mixlab_stopLive) {
            window._mixlab_stopLive()
            window._mixlab_stopLive = null
            widget.liveBtn.innerText = 'Live Run'
          } else {
            window._mixlab_stopLive = await startLive(widget.liveBtn)
            console.log('window._mixlab_stopLive', window._mixlab_stopLive)
          }
        })

        widget.openFloatingWinBtn.addEventListener('click', async () => {
          // if (window._mixlab_stopLive) {
          //   window._mixlab_stopLive()
          //   window._mixlab_stopLive = null
          //   widget.liveBtn.innerText = 'Live Run'
          // }
          let blob = await createBlobFromVideoForArea(
            window._mixlab_screen_webcamVideo
          )

          setArea(await blobToBase64(blob))
        })
        // console.log('widget.inputEl',widget.inputEl)

        /*
              Add the widget, make sure we clean up nicely, and we do not want to be serialized!
              */
        this.addCustomWidget(widget)
        this.onRemoved = function () {
          widget.preview.remove()
          widget.shareDiv.remove()
          widget.shareOfWebCamBtn.remove()
          widget.shareBtn.remove()
          widget.liveBtn.remove()
          widget.card.remove()
          widget.refreshInput.remove()
          widget.previewArea.remove()
          widget.previewCard.remove()
        }
        this.serialize_widgets = true
      }
    }
  }
})

function updateSetAreaDisplay () {
  try {
    let canvas = document.createElement('canvas')
    canvas.width = window._mixlab_screen_webcamVideo.videoWidth
    canvas.height = window._mixlab_screen_webcamVideo.videoHeight
    let ctx = canvas.getContext('2d')
    const lineWidth = 2 // Width of the stroke line
    const strokeColor = 'red' // Color of the stroke

    // Draw the rectangle
    ctx.strokeStyle = strokeColor // Set the stroke color
    ctx.lineWidth = lineWidth // Set the stroke line width

    ctx.fillStyle = 'rgba(255,0,0,0.35)'

    let x = 0,
      y = 0,
      width = canvas.width,
      height = canvas.height

    if (!window._mixlab_share_screen) {
      let d = getSetAreaData()
      if (d) {
        window._mixlab_share_screen = d
      }
    }

    if (window._mixlab_share_screen) {
      x = window._mixlab_share_screen.x
      y = window._mixlab_share_screen.y
      width = window._mixlab_share_screen.width
      height = window._mixlab_share_screen.height
    }

    ctx.strokeRect(x, y, width, height) // Draw the stroked rectangle
    ctx.fillRect(x, y, width, height)

    canvas.style.width = '100%'

    let area = graph._nodes
      .filter(n => n.type === 'ScreenShare')[0]
      .widgets.filter(w => w.name == 'sreen_share')[0].previewArea

    area.innerHTML = ''
    area.appendChild(canvas)
    area.style = `
    position: absolute;
    width:100%%;
    left:0;
    top:0;
    `
  } catch (error) {
    console.log(error)
  }
}

function updateSetAreaData (left, top, width, height, imgWidth, imgHeight) {
  window._mixlab_share_screen = {
    x: left,
    y: top,
    width,
    height,
    imgWidth,
    imgHeight
  }
  localStorage.setItem(
    '_mixlab_share_screen',
    JSON.stringify(window._mixlab_share_screen)
  )
}

function getSetAreaData () {
  try {
    let data = JSON.parse(localStorage.getItem('_mixlab_share_screen')) || {}
    if (data.width === 0 || data.height === 0 || data.width === undefined)
      return
    return data
  } catch (error) {}
  return
}

async function setArea (src) {
  let displayHeight = Math.round(window.screen.availHeight * 0.6)
  let div = document.createElement('div')
  div.innerHTML = `
    <div id='ml_overlay' style='position: absolute;top:0;background: #251f1fc4;
    height: 100vh;
    width: 100%;'>
      <img id='ml_video' style='position: absolute; 
      height: ${displayHeight}px;user-select: none; 
      -webkit-user-drag: none;
      outline: 2px solid #eaeaea;
      box-shadow: 8px 9px 17px #575757;' />
      <div id='ml_selection' style='position: absolute; 
      border: 2px dashed red; 
      pointer-events: none;'></div>
    </div>`
  // document.body.querySelector('#ml_overlay')
  document.body.appendChild(div)

  let im = await createImage(src)

  let img = div.querySelector('#ml_video')
  let overlay = div.querySelector('#ml_overlay')
  let selection = div.querySelector('#ml_selection')
  let startX, startY, endX, endY
  let start = false
  // Set video source
  img.src = src

  // init area
  const data = getSetAreaData()
  let x = 0,
    y = 0,
    width = (im.naturalWidth * displayHeight) / im.naturalHeight,
    height = displayHeight
  let imgWidth = im.naturalWidth
  let imgHeight = im.naturalHeight
  // console.log(
  //   '#screen_share::使用上一次选区 selection',
  //   data,
  //   imgWidth,
  //   img.width
  // )
  if (
    data &&
    data.width > 0 &&
    data.height > 0 &&
    data.imgWidth === imgWidth &&
    data.imgHeight === imgHeight &&
    data.imgHeight > 0
  ) {
    // 相同尺寸窗口，恢复选区
    x = (img.width * data.x) / data.imgWidth
    y = (img.height * data.y) / data.imgHeight
    width = (img.width * data.width) / data.imgWidth
    height = (img.height * data.height) / data.imgHeight
    // imgWidth = data.imgWidth
    // imgHeight = data.imgHeight;
    // console.log('#screen_share::使用上一次选区 selection', x, y, width, height)
  }

  selection.style.left = x + 'px'
  selection.style.top = y + 'px'
  selection.style.width = width + 'px'
  selection.style.height = height + 'px'

  // Add mouse events
  img.addEventListener('mousedown', startSelection)
  img.addEventListener('mousemove', updateSelection)
  img.addEventListener('mouseup', endSelection)
  overlay.addEventListener('click', remove)

  function remove () {
    overlay.removeEventListener('click', remove)
    img.removeEventListener('mousedown', startSelection)
    img.removeEventListener('mousemove', updateSelection)
    img.removeEventListener('mouseup', endSelection)
    div.remove()
  }

  function startSelection (event) {
    if (start == false) {
      startX = event.clientX
      startY = event.clientY
      updateSelection(event)
      start = true
    } else {
    }
  }

  function updateSelection (event) {
    endX = event.clientX
    endY = event.clientY

    // Calculate width, height, and coordinates
    let width = Math.abs(endX - startX)
    let height = Math.abs(endY - startY)
    let left = Math.min(startX, endX)
    let top = Math.min(startY, endY)

    // Set selection style
    selection.style.left = left + 'px'
    selection.style.top = top + 'px'
    selection.style.width = width + 'px'
    selection.style.height = height + 'px'
  }

  function endSelection (event) {
    endX = event.clientX
    endY = event.clientY

    // 获取img元素的真实宽度和高度
    let imgWidth = img.naturalWidth
    let imgHeight = img.naturalHeight

    // 换算起始坐标
    let realStartX = (startX / img.offsetWidth) * imgWidth
    let realStartY = (startY / img.offsetHeight) * imgHeight

    // 换算起始坐标
    let realEndX = (endX / img.offsetWidth) * imgWidth
    let realEndY = (endY / img.offsetHeight) * imgHeight

    // 输出结果到控制台
    // console.log('真实宽度: ' + realWidth)
    // console.log('真实高度: ' + realHeight)
    startX = realStartX
    startY = realStartY
    endX = realEndX
    endY = realEndY
    // Calculate width, height, and coordinates
    let width = Math.abs(endX - startX)
    let height = Math.abs(endY - startY)
    let left = Math.min(startX, endX)
    let top = Math.min(startY, endY)
    // Output results to console
    // console.log('坐标位置: (' + left + ', ' + top + ')')
    // console.log('宽度: ' + width)
    // console.log('高度: ' + height)

    // img.removeEventListener('mousedown', startSelection)
    // img.removeEventListener('mousemove', updateSelection)
    // img.removeEventListener('mouseup', endSelection)

    // window._mixlab_screen_x = left
    // window._mixlab_screen_y = top
    // window._mixlab_screen_width = width
    // window._mixlab_screen_height = height

    if (width <= 0 && height <= 0) return remove()

    updateSetAreaData(left, top, width, height, imgWidth, imgHeight)

    updateSetAreaDisplay()

    createBlobFromVideo(
      window._mixlab_screen_webcamVideo,
      !window._mixlab_screen_live
    )

    remove()
  }
}

async function save_workflow (json) {
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`

  const res = await fetch(`${url}/mixlab/workflow`, {
    method: 'POST',
    body: JSON.stringify({
      data: json,
      task: 'save'
    })
  })
  return await res.json()
}

async function get_my_workflow () {
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`

  const res = await fetch(`${url}/mixlab/workflow`, {
    method: 'POST',
    body: JSON.stringify({
      task: 'list'
    })
  })
  let result = await res.json()
  return result.data
}

app.registerExtension({
  name: 'Mixlab.image.FloatingVideo',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'FloatingVideo') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)

        const widget = {
          type: 'video',
          name: 'FloatingVideo',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.card.style,
              get_position_style(ctx, widget_width, y, node.size[1])
            )
          }
        }

        widget.card = $el('div', {})

        widget.preview = $el('video', {
          controls: true,
          draggable: true,
          style: {
            width: '100%'
          },
          poster:
            'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAAAXNSR0IArs4c6QAAALZJREFUKFOFkLERwjAQBPdbgBkInECGaMLUQDsE0AkRVRAYWqAByxldPPOWHwnw4OBGye1p50UDSoA+W2ABLPN7i+C5dyC6R/uiAUXRQCs0bXoNIu4QPQzAxDKxHoALOrZcqtiyR/T6CXw7+3IGHhkYcy6BOR2izwT8LptG8rbMiCRAUb+CQ6WzQVb0SNOi5Z2/nX35DRyb/ENazhpWKoGwrpD6nICp5c2qogc4of+c7QcrhgF4Aa/aoAFHiL+RAAAAAElFTkSuQmCC'
        })

        // })
        // const dropTarget = document.getElementById('your-drop-target-id')

        // dropTarget.addEventListener('dragover', event => {
        //   event.preventDefault()
        // })

        // dropTarget.addEventListener('drop', event => {
        //   event.preventDefault()

        //   const imageUrl = event.dataTransfer.getData('text/plain')

        //   navigator.clipboard
        //     .writeText(imageUrl)
        //     .then(() => {
        //       console.log('Image URL copied to clipboard')
        //     })
        //     .catch(error => {
        //       console.error('Failed to copy image URL to clipboard:', error)
        //     })
        // })

        widget.canvas = $el('canvas', {
          style: {
            display: 'none'
          }
        })

        widget.PictureInPicture = $el('button', {
          innerText: 'PictureInPicture',
          style: {
            display: 'pictureInPictureEnabled' in document ? 'block' : 'none',
            cursor: 'pointer',
            padding: '8px 0',
            fontWeight: '300',
            margin: '2px'
          }
        })

        document.body.appendChild(widget.card)
        widget.card.appendChild(widget.PictureInPicture)
        widget.card.appendChild(widget.preview)
        widget.card.appendChild(widget.canvas)

        widget.preview.addEventListener('click', event => {
          const imageUrl = window._mixlab_screen_result || ''
          // console.log(imageUrl)
          try {
            if (imageUrl) clipboardWriteImage(pipWindow, imageUrl)
          } catch (error) {
            console.log(error)
            if (imageUrl) clipboardWriteImage(window, imageUrl)
          }

          // pipWindow.navigator.permissions
          //   .query({ name: 'clipboard-write' })
          //   .then(result => {
          //     if (result.state === 'granted' || result.state === 'prompt') {
          //       // 执行复制操作

          //     } else {
          //       console.error('Clipboard write permission denied')
          //     }
          //   })
        })

        // widget.card.appendChild(widget.PictureInPicture)

        widget.PictureInPicture.addEventListener('click', async () => {
          if (window.location.protocol != 'https:') {
            let http_workflow = app.graph.serialize()
            await save_workflow(http_workflow)

            window.alert(
              `Redirecting to HTTPS access due to the requirement of the floating window. https://${
                window.location.hostname
              }:${~~window.location.port + 1}`
            )
            window.open(
              `https://${window.location.hostname}:${
                ~~window.location.port + 1
              }?workflow=1`
            )
          }
          // Open a Picture-in-Picture window.
          let w = 360,
            s = widget.preview.videoWidth / widget.preview.videoHeight,
            h = w / s || w
          console.log(h)

          const pipWindow = await documentPictureInPicture.requestWindow({
            width: w,
            height: Math.round(h) + 120
          })

          pipWindow.document.body.style = `margin: 0px;
          overflow: hidden;
          background: #2a2c34;
          border: 4px solid #878787;
          outline: none;background: black;`

          let div = document.createElement('div')
          div.style = `display:flex;position: fixed;flex-direction: column;
          bottom: 0px;
          z-index: 9999;
          left: 0px;
          width: calc(100% - 24px);
          margin: 12px;`

          let inputDiv = document.createElement('div')
          inputDiv.style = `width: 100%;`

          // inputDiv.style = ``
          let infoDiv = document.createElement('div')
          infoDiv.style = `width: 100%;
          display: flex;
          justify-content: space-between;
          height: 16px;
          color: white;
          margin-bottom: 4px;
          font-size: 12px;
          text-shadow: gray 1px 1px;
          align-items: center;`

          let infoText = document.createElement('div')
          infoText.id = 'info'

          let hideBtn = document.createElement('button')
          hideBtn.innerText = '🤖'
          hideBtn.style = `
          border: none;
          background: none;
          cursor: pointer; height: 24px; margin: 4px; color: red;`

          hideBtn.addEventListener('click', () => {
            if (fnDiv.style.display == 'none') {
              fnDiv.style.display = 'flex'
            } else {
              fnDiv.style.display = 'none'
            }
            try {
              pipWindow.document.querySelector('#info').innerText = ''
            } catch (error) {
              console.log(error)
            }
          })

          // Move the player to the Picture-in-Picture window.
          let input = document.createElement('textarea')
          input.style = `
          min-width:90%;
          max-width:100%;
          background: #24283db3;
          color: white;
          font-size: 14px;
          padding: 8px;
          font-weight: 300;
          letter-spacing: 1px;
          outline: none;
          min-height: 98px;
          border-radius: 8px;
          border: 1px solid rgb(91, 91, 91);
          font-family: sans-serif;
          `
          // Create a style element
          const style = document.createElement('style')
          // Define the CSS rule for scrollbar width
          const cssRule = `::-webkit-scrollbar { width: 2px;}`
          // Add the CSS rule to the style element
          style.appendChild(document.createTextNode(cssRule))

          // Append the style element to the document head
          pipWindow.document.head.appendChild(style)

          window._mixlab_screen_prompt =
            window._mixlab_screen_prompt ||
            'beautiful scenery nature glass bottle landscape,under water'
          input.value = window._mixlab_screen_prompt

          let btnDiv = document.createElement('div')

          btnDiv.style = `cursor: pointer;
          display: flex;
          flex-direction: column;
          justify-content: start;
          align-items: center;
          width: 24px;
          font-size: 16px;
          margin-right: 6px;user-select: none;`

          let seedBtn = document.createElement('butotn')
          seedBtn.innerText = '🎲'
          seedBtn.style = `cursor: pointer;height: 24px;margin:4px;
          color: red;`

          seedBtn.addEventListener('click', () => {
            window._mixlab_screen_seed_input = Math.round(
              Math.floor(Math.random() * 0xffffffffffffffff)
            )

            try {
              pipWindow.document.querySelector('#info').innerText =window._mixlab_screen_seed_input
            } catch (error) {
              console.log(error)
            }

            // console.log(window._mixlab_screen_seed_input)
            if (window._mixlab_screen_blob)
              document.querySelector('#queue-button').click()
          })

          // TODO 需要判断是否有screenshare节点，没有的话，不需要添加
          let pauseBtn = document.createElement('butotn')
          pauseBtn.innerText = '⏸'
          pauseBtn.style = `cursor: pointer;height: 24px;margin:4px;
          color: #03A9F4;`

          pauseBtn.addEventListener('click', async () => {
            if (window._mixlab_stopLive) {
              pauseBtn.innerText = '▶'

              window._mixlab_stopLive()
              window._mixlab_stopLive = null

              let node = this.graph._nodes.filter(
                n => n.type === 'ScreenShare'
              )[0]

              var w = node.widgets?.filter(w => w.name === 'sreen_share')[0] // see if it already exists
              if (w) {
                w.liveBtn.innerText = 'Live Run'
              }

              try {
                pipWindow.document.querySelector('#info').innerText =
                  'Stop Live'
              } catch (error) {
                console.log(error)
              }
            } else {
              pauseBtn.innerText = '⏸'
              let node = this.graph._nodes.filter(
                n => n.type === 'ScreenShare'
              )[0]
              var w = node.widgets?.filter(w => w.name === 'sreen_share')[0] // see if it already exists
              if (w) {
                w.liveBtn.innerText = 'Stop Live'
                window._mixlab_stopLive = await startLive(w.liveBtn)
                console.log('window._mixlab_stopLive', window._mixlab_stopLive)
              }

              try {
                pipWindow.document.querySelector('#info').innerText = 'Live'
              } catch (error) {
                console.log(error)
              }
            }
          })

          let promptFinishBtn = document.createElement('butotn')
          promptFinishBtn.innerText = '🚀'
          promptFinishBtn.style = `cursor: pointer;height: 24px;margin:4px;`
          promptFinishBtn.addEventListener('click', () => {
            console.log('##更新Prompt')
            window._mixlab_screen_prompt =
              window._mixlab_screen_prompt_input || window._mixlab_screen_prompt

            if (window._mixlab_screen_blob)
              document.querySelector('#queue-button').click()

            try {
              pipWindow.document.querySelector('#info').innerText =
                'Update Prompt'
            } catch (error) {
              console.log(error)
            }
          })

          widget.preview.addEventListener('click', event => {
            const imageUrl = window._mixlab_screen_result || ''
            // console.log(imageUrl)
            try {
              if (imageUrl) clipboardWriteImage(pipWindow, imageUrl)
            } catch (error) {
              console.log(error)
              if (imageUrl) clipboardWriteImage(window, imageUrl)
            }

            try {
              pipWindow.document.querySelector('#info').innerText =
                'Image copied to clipboard'
              setTimeout(
                () =>
                  (pipWindow.document.querySelector('#info').innerText = ''),
                8000
              )
            } catch (error) {
              console.log(error)
            }
            // pipWindow.navigator.permissions
            //   .query({ name: 'clipboard-write' })
            //   .then(result => {
            //     if (result.state === 'granted' || result.state === 'prompt') {
            //       // 执行复制操作

            //     } else {
            //       console.error('Clipboard write permission denied')
            //     }
            //   })
          })

          pipWindow.document.body.append(widget.preview)
          pipWindow.document.body.append(div)

          // 滑动条
          const createSlide = () => {
            let d = document.createElement('div')
            d.style = `width: 100%;margin-bottom: 12px;`
            let range = document.createElement('input')
            range.type = 'range'
            d.appendChild(range)
            return range
          }

          let slideInp = createSlide()
          slideInp.addEventListener('change', () => {
            console.log(~~slideInp.value / 100)
            window._mixlab_screen_slide_input = ~~slideInp.value / 100
            try {
              pipWindow.document.querySelector('#info').innerText =
                window._mixlab_screen_slide_input
              if (window._mixlab_screen_blob)
                document.querySelector('#queue-button').click()
            } catch (error) {
              console.log(error)
            }
          })

          // console.log(pipWindow)

          let fnDiv = document.createElement('div')
          fnDiv.style = `display: flex;`

          div.appendChild(infoDiv)
          div.appendChild(fnDiv)

          infoDiv.appendChild(infoText)
          infoDiv.appendChild(hideBtn)

          fnDiv.appendChild(btnDiv)
          // 按钮区域
          btnDiv.appendChild(seedBtn)
          btnDiv.appendChild(pauseBtn)
          btnDiv.appendChild(promptFinishBtn)

          // 输入框
          fnDiv.appendChild(inputDiv)
          inputDiv.appendChild(slideInp)

          inputDiv.appendChild(input)

          input.addEventListener('input', () => {
            window._mixlab_screen_prompt_input = input.value
            try {
              pipWindow.document.querySelector('#info').innerText = ''
            } catch (error) {
              console.log(error)
            }
          })

          input.addEventListener('keydown', handleKeyDown)

          function handleKeyDown (event) {
            if (event.key === 'Enter') {
              if (!event.shiftKey) {
                // 回车键被按下且未同时按下Shift键，执行你的操作
                event.preventDefault() // 阻止默认行为（如提交表单）
                // 在这里添加你的代码
                console.log('##更新Prompt')
                window._mixlab_screen_prompt =
                  window._mixlab_screen_prompt_input ||
                  window._mixlab_screen_prompt

                if (window._mixlab_screen_blob)
                  document.querySelector('#queue-button').click()

                try {
                  pipWindow.document.querySelector('#info').innerText =
                    'Update Prompt'
                } catch (error) {
                  console.log(error)
                }
              }
            }
          }

          // Move the player back when the Picture-in-Picture window closes.
          pipWindow.addEventListener('pagehide', event => {
            widget.card.appendChild(widget.preview)
            // pipWindow.remove()
            pipWindow.close()
          })
        })

        this.addCustomWidget(widget)
        this.onRemoved = function () {
          widget.preview.remove()
          widget.canvas.remove()
          widget.card.remove()
          widget.PictureInPicture.remove()
        }
        this.serialize_widgets = true
      }

      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        const r = onExecuted ? onExecuted.apply(this, message) : undefined

        if (this.widgets) {
          const video = this.widgets.filter(w => w.type === `video`)[0]
          const canvas = video.canvas

          if (video.preview.paused) {
            const stream = canvas.captureStream()
            const videoTrack = stream.getVideoTracks()[0]

            video.preview.srcObject = new MediaStream([videoTrack])
            try {
              video.preview.play()
            } catch (error) {
              console.log(error)
            }

            // 检查浏览器是否支持画中画模式
            if ('pictureInPictureEnabled' in document) {
              // 检查video元素是否可以进入画中画模式
              // if (video.preview !== document.pictureInPictureElement) {
              //   // 请求进入画中画模式
              //   video.preview.addEventListener('loadedmetadata', () => {
              //     // 请求进入画中画模式
              //     video.preview
              //       .requestPictureInPicture()
              //       .then(() => {
              //         // 进入画中画模式成功
              //         console.log('进入画中画模式成功')
              //       })
              //       .catch(error => {
              //         // 进入画中画模式失败
              //         console.error('进入画中画模式失败', error)
              //       })
              //   })
              // } else {
              //   // 已经在画中画模式中
              //   console.log('已经在画中画模式中')
              // }
            } else {
              // 浏览器不支持画中画模式
              console.error('浏览器不支持画中画模式')
            }
          }

          const context = canvas.getContext('2d')

          if (message?.images_) {
            window._mixlab_screen_result = `data:image/png;base64,${message.images_[0]}`
            const image = new Image()
            image.onload = function () {
              canvas.width = image.width
              canvas.height = image.height
              context.drawImage(image, 0, 0)
            }
            // console.log(`data:image/jpeg;base64,${base64}`)
            image.src = window._mixlab_screen_result
          }
          const onRemoved = this.onRemoved
          this.onRemoved = () => {
            // cleanupNode(this)
            return onRemoved?.()
          }
        }
        this.setSize([
          this.size[0],
          this.computeSize([this.size[0], this.size[1]])[1]
        ])
        return r
      }
    }
  }
})

// ;(() => {
//   // 创建一个新的style元素
//   var styleElement = document.createElement('style')

//   // 设置样式内容
//   var cssCode = `
//   :picture-in-picture {
//     box-shadow: 0 0 0 5px red;
//   }
// `
//   // 将样式内容添加到style元素中
//   styleElement.appendChild(document.createTextNode(cssCode))

//   // 将style元素添加到文档头部
//   document.head.appendChild(styleElement)
// })()

// 和python实现一样
function run (mutable_prompt, immutable_prompt) {
  // Split the text into an array of words
  const words1 = mutable_prompt.split('\n')

  // Split the text into an array of words
  const words2 = immutable_prompt.split('\n')

  const prompts = []
  for (let i = 0; i < words1.length; i++) {
    words1[i] = words1[i].trim()
    for (let j = 0; j < words2.length; j++) {
      words2[j] = words2[j].trim()
      if (words2[j] && words1[i]) {
        prompts.push(words2[j].replaceAll('``', words1[i]))
      }
    }
  }

  return prompts
}

// 更新ui，计算prompt的组合结果
const updateUI = node => {
  const mutable_prompt_w = node.widgets.filter(
    w => w.name === 'mutable_prompt'
  )[0]
  mutable_prompt_w.inputEl.title = 'Enter keywords, one per line'
  const immutable_prompt_w = node.widgets.filter(
    w => w.name === 'immutable_prompt'
  )[0]
  immutable_prompt_w.inputEl.title =
    'Enter prompts, one per line, variables represented by ``'

  const max_count = node.widgets.filter(w => w.name === 'max_count')[0]
  let prompts = run(mutable_prompt_w.value, immutable_prompt_w.value)

  prompts = prompts.slice(0, max_count.value)

  max_count.value = prompts.length

  // 如果已经存在,删除
  const pw = node.widgets.filter(w => w.name === 'prompts')[0]
  if (pw) {
    // node.widgets[pos].onRemove?.();
    pw.value = prompts.join('\n\n')
    pw.inputEl.title = `Total of ${prompts.length} prompts`
  } else {
    // 动态添加
    const w = ComfyWidgets.STRING(
      node,
      'prompts',
      ['STRING', { multiline: true }],
      app
    ).widget
    w.inputEl.readOnly = true
    w.inputEl.style.opacity = 0.6
    w.value = prompts.join('\n\n')
    w.inputEl.title = `Total of ${prompts.length} prompts`
  }

  // 移除无关的widget
  //  for (let i = 0; i < node.widgets.length; i++) {
  //   console.log(node.widgets[i]?.name)
  //   if(node.widgets[i]&&!['mutable_prompt','immutable_prompt','max_count','prompts'].includes(node.widgets[i].name)) node.widgets[i].onRemove?.();
  // }

  // console.log(node.widgets.length,node.size);

  node.widgets.length = 5
  node.onResize?.(node.size)
}

const exportGraph = () => {
  const graph = app.graph

  var clipboard_info = {
    nodes: [],
    links: []
  }
  var index = 0
  var selected_nodes_array = []
  for (var i in graph._nodes_in_order) {
    var node = graph._nodes_in_order[i]
    if (node.clonable === false) continue
    node._relative_id = index
    selected_nodes_array.push(node)
    index += 1
  }

  for (var i = 0; i < selected_nodes_array.length; ++i) {
    var node = selected_nodes_array[i]
    var cloned = node.clone()
    if (!cloned) {
      console.warn('node type not found: ' + node.type)
      continue
    }

    let nc = {}
    let n = cloned.serialize()
    for (const key in n) {
      if (
        [
          'type',
          'pos',
          'size',
          'flags',
          'order',
          'mode',
          'inputs',
          'outputs',
          'properties',
          'widgets_values'
        ].includes(key)
      ) {
        nc[key] = n[key]
      }
    }

    clipboard_info.nodes.push(nc)

    if (node.inputs && node.inputs.length) {
      for (var j = 0; j < node.inputs.length; ++j) {
        var input = node.inputs[j]
        if (!input || input.link == null) {
          continue
        }
        var link_info = graph.links[input.link]
        if (!link_info) {
          continue
        }
        var target_node = graph.getNodeById(link_info.origin_id)
        if (!target_node) {
          continue
        }
        clipboard_info.links.push([
          target_node._relative_id,
          link_info.origin_slot, //j,
          node._relative_id,
          link_info.target_slot,
          target_node.id
        ])
      }
    }
  }
  localStorage.setItem('_Mixlab_clipboard', JSON.stringify(clipboard_info))

  return clipboard_info
}

const my = {
  nodes: [
    {
      type: 'LoadImage',
      pos: [719.5130480797907, 172.9437092123179],
      size: { 0: 315, 1: 314 },
      flags: {},
      order: 0,
      mode: 0,
      outputs: [
        { name: 'IMAGE', type: 'IMAGE', links: [], shape: 3 },
        { name: 'MASK', type: 'MASK', links: null, shape: 3 }
      ],
      properties: { 'Node name for S&R': 'LoadImage' },
      widgets_values: ['00204211b3c71288c12ed66516a1a20a.jpg', 'image']
    },
    {
      type: 'ControlNetLoader',
      pos: [1199.5130480797907, -331.0562907876821],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 1,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11p_sd15_canny.pth']
    },
    {
      type: 'ControlNetLoader',
      pos: [1204.5130480797907, -169.0562907876821],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 2,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11f1p_sd15_depth.pth']
    },
    {
      type: 'ControlNetLoader',
      pos: [1206.5130480797907, -20.056290787682087],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 3,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['t2iadapter_seg-fp16.safetensors']
    },
    {
      type: 'ControlNetLoader',
      pos: [1209.5130480797907, 125.94370921231791],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 4,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11p_sd15_openpose.pth']
    },
    {
      type: 'ControlNetLoader',
      pos: [1214.5130480797907, 293.9437092123179],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 5,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11e_sd15_ip2p.safetensors']
    },
    {
      type: 'ControlNetLoader',
      pos: [1212.5130480797907, 461.9437092123179],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 6,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11p_sd15_inpaint.pth']
    },
    {
      type: 'ControlNetLoader',
      pos: [1216.5130480797907, 636.9437092123179],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 7,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11f1e_sd15_tile.bin']
    },
    {
      type: 'ControlNetLoader',
      pos: [1227.5130480797907, 804.9437092123179],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 8,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11f1e_sd15_tile.bin']
    },
    {
      type: 'ControlNetApplyAdvanced',
      pos: [1816, 94],
      size: { 0: 315, 1: 166 },
      flags: {},
      order: 9,
      mode: 0,
      inputs: [
        { name: 'positive', type: 'CONDITIONING', link: null },
        { name: 'negative', type: 'CONDITIONING', link: null },
        { name: 'control_net', type: 'CONTROL_NET', link: null, slot_index: 2 },
        { name: 'image', type: 'IMAGE', link: null, slot_index: 3 }
      ],
      outputs: [
        { name: 'positive', type: 'CONDITIONING', links: null, shape: 3 },
        { name: 'negative', type: 'CONDITIONING', links: null, shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetApplyAdvanced' },
      widgets_values: [1, 0, 1]
    }
  ],
  links: [
    [1, 0, 9, 2, 2],
    [0, 0, 9, 3, 1]
  ]
}

// 添加workflow
const importWorkflow = my => {
  localStorage.setItem('litegrapheditor_clipboard', JSON.stringify(my))
  app.canvas.pasteFromClipboard()
}

function getURLParameters (url) {
  var params = {}
  var paramStr = url.split('?')[1]
  if (paramStr) {
    var paramArr = paramStr.split('&')
    for (var i = 0; i < paramArr.length; i++) {
      var param = paramArr[i].split('=')
      var paramName = decodeURIComponent(param[0])
      var paramValue = decodeURIComponent(param[1] || '')
      if (paramName) {
        if (params[paramName]) {
          params[paramName] = Array.isArray(params[paramName])
            ? [...params[paramName], paramValue]
            : [params[paramName], paramValue]
        } else {
          params[paramName] = paramValue
        }
      }
    }
  }
  return params
}

// var url = "http://example.com/page?param1=value1&param2=value2&param3=value3";
// var params = getURLParameters(url);
// console.log(params);

const node = {
  name: 'RandomPrompt',
  async init (app) {
    // Any initial setup to run as soon as the page loads
    console.log('[logging]', 'extension init')

    if (window.location.href.match('/?')) {
      const { workflow } = getURLParameters(window.location.href)
      if (workflow)
        get_my_workflow().then(data => {
          console.log('#get_my_workflow', data)
          let my_workflow = data.filter(
            d => d.filename == 'my_workflow.json'
          )[0]
          if (my_workflow?.data) {
            // app.loadGraphData(my_workflow.data)
            localStorage.setItem('workflow', JSON.stringify(my_workflow.data))
          }
        })
    }
  },
  async setup (a) {
    for (const node of app.graph._nodes) {
      // console.log('#setup', node)
      if (node.type === 'RandomPrompt') {
        updateUI(node)
      }
    }
    // console.log('[logging]', 'loaded graph node: ', exportGraph(app.graph))
  },
  addCustomNodeDefs (defs, app) {
    // console.log(
    //   '[logging]',
    //   'add custom node definitions',
    //   'current nodes:',
    //   defs
    // )
    // 在这里进行 语言切换
    // for (const nodeName in defs) {
    //   if (nodeName === 'RandomPrompt') {
    //     // defs[nodeName].category
    //     // defs[nodeName].display_name
    //   }
    // }
  },
  loadedGraphNode (node, app) {
    // Fires for each node when loading/dragging/etc a workflow json or png
    // If you break something in the backend and want to patch workflows in the frontend
    // This is the place to do this
    // console.log("[logging]", "loaded graph node: ", exportGraph(node.graph));
  },
  async nodeCreated (node) {
    if (node.type === 'RandomPrompt') {
      updateUI(node)
    }

    if (node.type === 'RunWorkflow') {
      const pw = node.widgets.filter(w => w.name === 'workflow')[0]
      console.log('nodeCreated', pw)
      // if (pw) {
      // 	// node.widgets[pos].onRemove?.();
      //   pw.value = prompts.join('\n\n');
      //   // pw.inputEl=document.createElement('input');
      // }

      //  node.widgets.length = 1;
      node.onResize?.(node.size)
    }
  },
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    // 注册节点前，可以修改节点的数据
    // 可以获取得到其他节点数据

    // 汉化
    // app.graph._nodes // title ='123'

    // if (nodeData.name === 'SaveTransparentImage') {
    //   const onExecuted = nodeType.prototype.onExecuted
    //   nodeType.prototype.onExecuted = function (message) {
    //     const r = onExecuted?.apply?.(this, arguments)
    //     console.log('executed', message)
    //     const { image_path } = message
    //     if (image_path) {
    //     }
    //     return r
    //   }
    // }

    if (nodeData.name === 'WSServer') {
      // Create the button widget for selecting the files
      // node.addWidget(
      //   'button',
      //   'choose file to upload',
      //   'video',
      //   () => {
      //     console.log('click')
      //   }
      // )
      // uploadWidget.serialize = false
      // const onExecuted = nodeType.prototype.onExecuted
      // nodeType.prototype.onExecuted = function (message) {
      //   const r = onExecuted?.apply?.(this, arguments)
      //   console.log('executed', message)
      //   const upload = this.widgets.filter(w => w.name === 'upload')[0]
      //   console.log('executed', this.widgets)
      //   // navigator.mediaDevices
      //   //   .getDisplayMedia({ video: true })
      //   //   .then(stream => {
      //   //     const videoElement = document.createElement('video')
      //   //     videoElement.srcObject = stream
      //   //     videoElement.autoplay = true
      //   //     const canvasElement = document.createElement('canvas')
      //   //     const context = canvasElement.getContext('2d')
      //   //     videoElement.addEventListener('loadedmetadata', () => {
      //   //       canvasElement.width = videoElement.videoWidth
      //   //       canvasElement.height = videoElement.videoHeight
      //   //       setInterval(async () => {
      //   //         context.drawImage(
      //   //           videoElement,
      //   //           0,
      //   //           0,
      //   //           canvasElement.width,
      //   //           canvasElement.height
      //   //         )
      //   //         const imageData = canvasElement.toDataURL()
      //   //         upload.value = await uploadScreenshot(imageData)
      //   //       }, 200)
      //   //     })
      //   //   })
      //   //   .catch(error => {
      //   //     console.error('Error getting screen share:', error)
      //   //   })
      //   return r
      // }
    }

    if (nodeData.name === 'RandomPrompt') {
      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        const r = onExecuted?.apply?.(this, arguments)

        let prompts = message.prompts
        console.log('executed', message)
        // console.log('#RandomPrompt', this.widgets)
        const pw = this.widgets.filter(w => w.name === 'prompts')[0]

        if (pw) {
          // node.widgets[pos].onRemove?.();
          pw.value = prompts.join('\n\n')
          pw.inputEl.title = `Total of ${prompts.length} prompts`
        } else {
          // 动态添加
          const w = ComfyWidgets.STRING(
            node,
            'prompts',
            ['STRING', { multiline: true }],
            app
          ).widget
          w.inputEl.readOnly = true
          w.inputEl.style.opacity = 0.6
          w.value = prompts.join('\n\n')
          w.inputEl.title = `Total of ${prompts.length} prompts`
        }

        this.widgets.length = 5

        this.onResize?.(this.size)

        return r
      }
    }
  }
}

app.registerExtension(node)
