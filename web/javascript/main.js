import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

let api_host = '127.0.0.1:8188'
let api_base = ''
let url = `http://${api_host}${api_base}`

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

async function shareScreen (webcamVideo, shareBtn, liveBtn) {
  try {
    // let webcamVideo = document.createElement('video')
    const mediaStream = await navigator.mediaDevices.getDisplayMedia({
      video: true
    })

    webcamVideo.removeEventListener('timeupdate', videoTimeUpdateHandler)
    webcamVideo.srcObject = mediaStream
    webcamVideo.onloadedmetadata = () => {
      webcamVideo.play()
      webcamVideo.addEventListener('timeupdate', videoTimeUpdateHandler)

      window._mixlab_screen_x = 0
      window._mixlab_screen_y = 0
      // console.log(webcamVideo)
      window._mixlab_screen_width = webcamVideo.videoWidth
      window._mixlab_screen_height = webcamVideo.videoHeight
    }

    mediaStream.addEventListener('inactive', handleStopSharing)

    // 停止共享的回调函数
    function handleStopSharing () {
      console.log('用户停止了共享')
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

async function startLive (btn) {
  if (btn) window._mixlab_screen_live = !window._mixlab_screen_live

  if (btn) btn.innerText = `Stop Live`
  // console.log('#ML', 'live run', window._mixlab_screen_time)
  if (window._mixlab_screen_time) {
    // console.log('#ML', 'live')
    return
  }
  const { Pending, Running } = await getQueue()
  // console.log('#ML', Pending, window._mixlab_screen_blob)
  if (Pending <= 1 && window._mixlab_screen_blob && Running === 0) {
    window._mixlab_screen_time = true
    // console.log(file)
    window._mixlab_screen_imagePath = await blobToBase64(
      window._mixlab_screen_blob
    )
    // await uploadFile(file)
    window._mixlab_screen_time = false
    document.querySelector('#queue-button').click()
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
  // imgElement.src = await blobToBase64(blob)
  return blob
}

async function createBlobFromVideo (webcamVideo) {
  const videoW = webcamVideo.videoWidth
  const videoH = webcamVideo.videoHeight
  const aspectRatio = videoW / videoH
  const WIDTH = window._mixlab_screen_width,
    HEIGHT = window._mixlab_screen_height
  const canvas = new OffscreenCanvas(WIDTH, HEIGHT)
  const ctx = canvas.getContext('2d')
  ctx.drawImage(
    webcamVideo,
    window._mixlab_screen_x,
    window._mixlab_screen_y,
    WIDTH,
    HEIGHT,
    0,
    0,
    WIDTH,
    HEIGHT
  )

  const blob = await canvas.convertToBlob({
    type: 'image/jpeg',
    quality: 1
  })
  // imgElement.src = await blobToBase64(blob)
  window._mixlab_screen_blob = blob
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
    // const file = new File([base64ToBlob(base64Df)], `screenshot_mixlab_df.jpeg`)
    // window._mixlab_screen_default = await uploadFile(file)

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
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node
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
        console.log('###widget', widget)
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
            Object.assign(
              this.card.style,
              get_position_style(ctx, widget_width, y, node.size[1])
            )
          }
        }

        widget.card = $el('div', {})

        widget.preview = $el('video', {
          style: {
            width: '100%'
          },
          controls: true,
          poster:
            'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAAAXNSR0IArs4c6QAAALZJREFUKFOFkLERwjAQBPdbgBkInECGaMLUQDsE0AkRVRAYWqAByxldPPOWHwnw4OBGye1p50UDSoA+W2ABLPN7i+C5dyC6R/uiAUXRQCs0bXoNIu4QPQzAxDKxHoALOrZcqtiyR/T6CXw7+3IGHhkYcy6BOR2izwT8LptG8rbMiCRAUb+CQ6WzQVb0SNOi5Z2/nX35DRyb/ENazhpWKoGwrpD6nICp5c2qogc4of+c7QcrhgF4Aa/aoAFHiL+RAAAAAElFTkSuQmCC'
        })
        widget.shareBtn = $el('button', {
          innerText: 'Share Screen',
          style: {
            cursor: 'pointer',
            padding: '8px 0',
            fontWeight: '300',
            margin: '2px'
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
        widget.card.appendChild(widget.preview)
        widget.card.appendChild(widget.shareBtn)
        widget.card.appendChild(widget.openFloatingWinBtn)
        widget.card.appendChild(widget.refreshInput)
        widget.card.appendChild(widget.liveBtn)
        // widget.inputEl.addEventListener('click', () => {
        //   shareScreen(widget.inputEl)
        // })

        widget.shareBtn.addEventListener('click', async () => {
          if (widget.preview.paused) {
            window._mixlab_stopVideo = await shareScreen(
              widget.preview,
              widget.shareBtn,
              widget.liveBtn
            )
            widget.shareBtn.innerText = 'Stop Share'
            console.log('视频已暂停')
            if (window._mixlab_stopLive) {
              window._mixlab_stopLive()
              window._mixlab_stopLive = null
              widget.liveBtn.innerText = 'Live Run'
            }
          } else {
            console.log('视频正在播放')
            if (window._mixlab_stopVideo) {
              window._mixlab_stopVideo()
              window._mixlab_stopVideo = null
              widget.shareBtn.innerText = 'Share Screen'
            }
            if (window._mixlab_stopLive) {
              window._mixlab_stopLive()
              window._mixlab_stopLive = null
              widget.liveBtn.innerText = 'Live Run'
            }
          }
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

            var node = this.graph._nodes.filter(n => n.type == 'ScreenShare')[0] // for you to look it up like this
            var w = node?.widgets.find(w => w.name === 'prompt') // and then it's just the same
            console.log('####node?.widgets', node?.widgets)
            if (w) {
              w.value = 'a girl'
              node.onResize?.(node.size)
            }
          }
        })

        widget.openFloatingWinBtn.addEventListener('click', async () => {
          // console.log()
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
          widget.shareBtn.remove()
          widget.liveBtn.remove()
          widget.card.remove()
          widget.refreshInput.remove()
        }
        this.serialize_widgets = false
      }
    }
  }
})

function setArea (src) {
  let div = document.createElement('div')
  div.innerHTML = `
    <div id='ml_overlay' style='position: absolute;top:0'>
      <img id='ml_video' style='position: absolute; width: 500px;   user-select: none; -webkit-user-drag: none;' />
      <div id='ml_selection' style='position: absolute; border: 2px dashed red; pointer-events: none;'></div>
    </div>`

  document.body.appendChild(div)

  let img = div.querySelector('#ml_video')
  let overlay = div.querySelector('#ml_overlay')
  let selection = div.querySelector('#ml_selection')
  let startX, startY, endX, endY
  let start = false
  // Set video source
  img.src = src

  // Add mouse events
  img.addEventListener('mousedown', startSelection)
  img.addEventListener('mousemove', updateSelection)
  img.addEventListener('mouseup', endSelection)

  function startSelection (event) {
    if (start == false) {
      startX = event.clientX
      startY = event.clientY
      updateSelection(event)
      start = true
    } else {
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

      img.removeEventListener('mousedown', startSelection)
      img.removeEventListener('mousemove', updateSelection)
      img.removeEventListener('mouseup', endSelection)
      div.remove()
      window._mixlab_screen_x = left
      window._mixlab_screen_y = top
      window._mixlab_screen_width = width
      window._mixlab_screen_height = height
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
  }
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
          style: {
            width: '100%'
          },
          poster:
            'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAAAXNSR0IArs4c6QAAALZJREFUKFOFkLERwjAQBPdbgBkInECGaMLUQDsE0AkRVRAYWqAByxldPPOWHwnw4OBGye1p50UDSoA+W2ABLPN7i+C5dyC6R/uiAUXRQCs0bXoNIu4QPQzAxDKxHoALOrZcqtiyR/T6CXw7+3IGHhkYcy6BOR2izwT8LptG8rbMiCRAUb+CQ6WzQVb0SNOi5Z2/nX35DRyb/ENazhpWKoGwrpD6nICp5c2qogc4of+c7QcrhgF4Aa/aoAFHiL+RAAAAAElFTkSuQmCC'
        })

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

        // widget.card.appendChild(widget.PictureInPicture)

        widget.PictureInPicture.addEventListener('click', async () => {
          // Open a Picture-in-Picture window.
          let w = 360,
            s = widget.preview.videoWidth / widget.preview.videoHeight,
            h = w / s
          const pipWindow = await documentPictureInPicture.requestWindow({
            width: w,
            height: Math.round(h) + 120
          })

          pipWindow.document.body.style = `margin: 0px;
          overflow: hidden;
          background: #2a2c34;
          border: 4px solid #878787;
          outline: none;`
          // console.log(pipWindow.document)
          // Move the player to the Picture-in-Picture window.
          let input = document.createElement('textarea')
          input.style = `width: 100%;
          margin: 12px;
          background: rgb(249, 249, 249);
          color: black;
          font-size: 16px;
          padding: 8px;
          font-weight: 800;
          letter-spacing: 1px;
          border-radius: 8px;
          border: 1px solid rgb(221, 221, 221);
          box-shadow: rgb(228, 228, 228) 1px 3px`
          pipWindow.document.body.append(widget.preview)
          pipWindow.document.body.append(input)
          input.addEventListener('input', () => {
            window._mixlab_screen_prompt = input.value
          })
          // Move the player back when the Picture-in-Picture window closes.
          pipWindow.addEventListener('pagehide', event => {
            widget.card.appendChild(widget.preview)
            pipWindow.remove()
          })
        })

        this.addCustomWidget(widget)
        this.onRemoved = function () {
          widget.preview.remove()
          widget.canvas.remove()
          widget.card.remove()
          widget.PictureInPicture.remove()
        }
        this.serialize_widgets = false
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
            video.preview.play()

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

          if (message?.images) {
            const base64 = message.images[0]
            const image = new Image()
            image.onload = function () {
              canvas.width = image.width
              canvas.height = image.height
              context.drawImage(image, 0, 0)
            }
            // console.log(`data:image/jpeg;base64,${base64}`)
            image.src = `data:image/jpeg;base64,${base64}`
          }
          const onRemoved = this.onRemoved
          this.onRemoved = () => {
            cleanupNode(this)
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

const node = {
  name: 'RandomPrompt',
  async setup (a) {
    for (const node of app.graph._nodes) {
      if (node.comfyClass === 'RandomPrompt') {
        console.log('#setup', node)
        updateUI(node)
      }
    }
    console.log('[logging]', 'loaded graph node: ', exportGraph(app.graph))
  },
  addCustomNodeDefs (defs, app) {
    console.log(
      '[logging]',
      'add custom node definitions',
      'current nodes:',
      defs
    )
    // 在这里进行 语言切换
    for (const nodeName in defs) {
      if (nodeName === 'RandomPrompt') {
        // defs[nodeName].category
        // defs[nodeName].display_name
      }
    }
  },
  loadedGraphNode (node, app) {
    // Fires for each node when loading/dragging/etc a workflow json or png
    // If you break something in the backend and want to patch workflows in the frontend
    // This is the place to do this
    // console.log("[logging]", "loaded graph node: ", exportGraph(node.graph));
  },
  async nodeCreated (node) {
    if (node.comfyClass === 'RandomPrompt') {
      updateUI(node)
    }

    if (node.comfyClass === 'RunWorkflow') {
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

    if (nodeData.name === 'SaveTransparentImage') {
      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        const r = onExecuted?.apply?.(this, arguments)
        console.log('executed', message)
        const { image_path } = message
        if (image_path) {
        }
        return r
      }
    }

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
