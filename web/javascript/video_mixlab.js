import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'

import { $el } from '../../../scripts/ui.js'
import { injectCSS } from './common.js'

import { get_position_style } from './common.js'

injectCSS(`
.hidden{
  display:none !important
}`)

function videoUpload (node, inputName, inputData, app) {
  const imageWidget = node.widgets.find(w => w.name === 'video')
  let uploadWidget

  const widget = {
    type: 'div',
    name: 'upload-preview',
    draw (ctx, node, widget_width, y, widget_height) {
      let d = {
        ...get_position_style(ctx, widget_width - 12, 220, node.size[1], 44),
        outline: '1px solid',
        top: `${widget_height + 24}px`
      }

      delete d.height

      Object.assign(this.div.style, d)
    }
  }

  widget.div = $el('div', {})
  widget.div.style.width = `120px`
  document.body.appendChild(widget.div)
  node.addCustomWidget(widget)
  // console.log('#imageWidget', imageWidget)
  const displayDiv = document.createElement('video')
  displayDiv.controls = true
  // displayDiv.style=`width:200px;height:200px`
  imageWidget.callback = () => {
    displayDiv.src = `/view?filename=${
      imageWidget.value
    }&type=input&subfolder=${''}&rand=${Math.random()}`

    // displayDiv.onloadedmetadata = function () {
    //   var frameCount = displayDiv.duration * displayDiv.webkitDecodedFrameCount
    //   console.log('视频帧数：' + frameCount)
    //   node.widgets.filter(w => w.name == 'video_segment_frames')[0].value =
    //     frameCount
    // }
  }

  if (imageWidget.value) {
    // console.log(imageWidget.value)
    displayDiv.src = `/view?filename=${
      imageWidget.value
    }&type=input&subfolder=${''}&rand=${Math.random()}`
  }

  widget.div.appendChild(displayDiv)

  const onRemoved = node.onRemoved
  node.onRemoved = () => {
    widget.div.remove()
    return onRemoved?.()
  }

  var default_value = imageWidget.value
  Object.defineProperty(imageWidget, 'value', {
    set: function (value) {
      this._real_value = value
    },

    get: function () {
      let value = ''
      if (this._real_value) {
        value = this._real_value
      } else {
        return default_value
      }

      if (value.filename) {
        let real_value = value
        value = ''
        if (real_value.subfolder) {
          value = real_value.subfolder + '/'
        }

        value += real_value.filename

        if (real_value.type && real_value.type !== 'input')
          value += ` [${real_value.type}]`
      }
      return value
    }
  })
  async function uploadFile (file, updateNode, pasted = false) {
    try {
      // Wrap file in formdata so it includes filename
      const body = new FormData()
      body.append('image', file)
      if (pasted) body.append('subfolder', 'pasted')
      const resp = await api.fetchApi('/upload/image', {
        method: 'POST',
        body
      })

      if (resp.status === 200) {
        const data = await resp.json()
        // Add the file to the dropdown list and update the widget value
        let path = data.name
        if (data.subfolder) path = data.subfolder + '/' + path

        if (!imageWidget.options.values.includes(path)) {
          imageWidget.options.values.push(path)
        }

        if (updateNode) {
          imageWidget.value = path
        }

        return `/view?filename=${path}&type=input&subfolder=${
          pasted ? 'pasted' : ''
        }&rand=${Math.random()}`
      } else {
        alert(resp.status + ' - ' + resp.statusText)
      }
    } catch (error) {
      alert(error)
    }
  }

  const fileInput = document.createElement('input')
  Object.assign(fileInput, {
    type: 'file',
    accept: 'video/*,.mkv,video/webm,video/mp4,video/x-matroska,image/gif',
    style: 'display: none',
    onchange: async () => {
      if (fileInput.files.length) {
        let file = fileInput.files[0]

        const url = await uploadFile(file, true)

        // console.log('fileInput', file)
        var reader = new FileReader()
        reader.onload = function () {
          displayDiv.src = url
          displayDiv.onloadedmetadata = function () {
            // var frameCount =
            //   displayDiv.duration * displayDiv.webkitDecodedFrameCount
            // console.log('视频帧数：' + frameCount)
            // node.widgets.filter(
            //   w => w.name == 'video_segment_frames'
            // )[0].value = frameCount
          }
        }
        reader.readAsDataURL(file)
      }
    }
  })
  document.body.append(fileInput)

  // Create the button widget for selecting the files
  uploadWidget = node.addWidget('button', 'upload file', 'video', () => {
    fileInput.click()
  })
  uploadWidget.serialize = false
  return { widget: uploadWidget }
}
ComfyWidgets.VIDEOUPLOAD_ = videoUpload

app.registerExtension({
  name: 'Mixlab.Video.LoadVideoAndSegment_',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeData?.name == 'LoadVideoAndSegment_') {
      nodeData.input.required.upload = ['VIDEOUPLOAD_']
    }
  },
  async loadedGraphNode (node, app) {
    if (node.type === 'LoadVideoAndSegment_') {
      const imageWidget = node.widgets.find(w => w.name === 'video')
      const uploadPreview = node.widgets.find(w => w.name === 'upload-preview')
      if (imageWidget.value) {
        // console.log(imageWidget.value)
        uploadPreview.div.querySelector('video').src = `/view?filename=${
          imageWidget.value
        }&type=input&subfolder=${''}&rand=${Math.random()}`
      }
    }
  }
})

function offsetDOMWidget (widget, ctx, node, widgetWidth, widgetY, height) {
  const margin = 10
  const elRect = ctx.canvas.getBoundingClientRect()
  const transform = new DOMMatrix()
    .scaleSelf(
      elRect.width / ctx.canvas.width,
      elRect.height / ctx.canvas.height
    )
    .multiplySelf(ctx.getTransform())
    .translateSelf(margin, widgetY + margin)

  const scale = new DOMMatrix().scaleSelf(transform.a, transform.d)

  Object.assign(widget.inputEl.style, {
    transformOrigin: '0 0',
    transform: scale,
    left: `${transform.a + transform.e + 44}px`,
    top: `${transform.d + transform.f + 24}px`,
    width: `${widgetWidth - 32}px`,
    height: `${(height || widget.parent?.inputHeight || 32) - margin * 2}px`,
    position: 'absolute',
    background: !node.color ? '' : node.color,
    color: !node.color ? '' : 'white',
    zIndex: 5 //app.graph._nodes.indexOf(node),
  })
}
 

export const hasWidgets = node => {
  if (!node.widgets || !node.widgets?.[Symbol.iterator]) {
    return false
  }
  return true
}

export const cleanupNode = node => {
  if (!hasWidgets(node)) {
    return
  }

  for (const w of node.widgets) {
    if (w.canvas) {
      w.canvas.remove()
    }
    if (w.inputEl) {
      w.inputEl.remove()
    }
    // calls the widget remove callback
    w.onRemoved?.()
  }
}

const createPreviewElement = (name, val, format) => {
  const [type] = format.split('/')
  const w = {
    name,
    type,
    value: val,
    draw: function (ctx, node, widgetWidth, widgetY, height) {
      const [cw, ch] = this.computeSize(widgetWidth)
      offsetDOMWidget(this, ctx, node, widgetWidth, widgetY, ch)
    },
    computeSize: function (_) {
      const ratio = this.inputRatio || 1
      const width = Math.max(220, this.parent.size[0])
      return [width, width / ratio + 10]
    },
    onRemoved: function () {
      if (this.inputEl) {
        this.inputEl.remove()
      }
    }
  }

  w.inputEl = document.createElement(type === 'video' ? 'video' : 'img')
  w.inputEl.src = w.value

  if (type === 'video' || format.match('.mp4')) {
    w.inputEl.setAttribute('type', 'video/webm')
    w.inputEl.autoplay = true
    w.inputEl.loop = true
    w.inputEl.controls = true
  }
  w.inputEl.onload = function () {
    w.inputRatio = w.inputEl.naturalWidth / w.inputEl.naturalHeight
  }
  document.body.appendChild(w.inputEl)
  return w
}

app.registerExtension({
  name: 'Mixlab.Video.ImageListReplace',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeData?.name == 'ImageListReplace_') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)
        const widget = {
          type: 'div',
          name: 'preview',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width - 12, 220, node.size[1], 44),
              {
                outline: '1px solid',
                display: 'flex',
                flexWrap: 'wrap',
                flexDirection: 'row',
                justifyContent: 'flex-start',
                top: `${widget_height + 24}px`
              }
            )
          }
        }

        widget.div = $el('div', {})
        widget.div.style.width = `120px`
        widget.div.className = 'hidden'
        document.body.appendChild(widget.div)
        this.addCustomWidget(widget)
        // console.log('#ImageListReplace', widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          widget.div.remove()
          return onRemoved?.()
        }
      }

      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        onExecuted?.apply(this, arguments)

        // let _image_replace = message._image_replace[0]
        // _image_replace = `/view?filename=${_image_replace.filename}&type=${
        //   _image_replace.type
        // }&subfolder=${_image_replace.subfolder}&rand=${Math.random()}`

        let preview = this.widgets.filter(w => w.name == 'preview')[0]

        if (message._images.length > 0) {
          preview.div.className = ''
          // console.log('#ImageListReplace', preview.div)
        }

        preview.div.innerHTML = ''
        for (const img_ of message._images) {
          let img = new Image()
          img.style = `width: 100px;
          margin: 4px;`
          img.src = `/view?filename=${img_.filename}&type=${
            img_.type
          }&subfolder=${img_.subfolder}&rand=${Math.random()}`
          preview.div.appendChild(img)
        }

        let start_index = this.widgets.filter(w => w.name == 'start_index')[0]
        let end_index = this.widgets.filter(w => w.name == 'end_index')[0]
        let invert = this.widgets.filter(w => w.name == 'invert')[0]
        let _sc = start_index.callback.bind(start_index)
        let _ec = end_index.callback.bind(end_index)

        const selectImages = () => {
          // console.log(v)
          let s = start_index.value,
            e = end_index.value
          let imgs = preview.div.querySelectorAll('img')
          for (let index = 0; index < imgs.length; index++) {
            if (invert.value) {
              imgs[index].style.outline =
                index >= s && index <= e ? 'none' : '4px solid #cbd3fe'
            } else {
              imgs[index].style.outline =
                index >= s && index <= e ? '4px solid #cbd3fe' : 'none'
            }
          }
        }

        selectImages()

        start_index.callback = v => {
          let s = v,
            e = end_index.value
          let imgs = preview.div.querySelectorAll('img')
          for (let index = 0; index < imgs.length; index++) {
            if (invert.value) {
              imgs[index].style.outline =
                index >= s && index <= e ? 'none' : '4px solid #cbd3fe'
            } else {
              imgs[index].style.outline =
                index >= s && index <= e ? '4px solid #cbd3fe' : 'none'
            }
          }

          _sc(v)
        }

        end_index.callback = v => {
          let s = start_index.value,
            e = v
          let imgs = preview.div.querySelectorAll('img')
          for (let index = 0; index < imgs.length; index++) {
            if (invert.value) {
              imgs[index].style.outline =
                index >= s && index <= e ? 'none' : '4px solid #cbd3fe'
            } else {
              imgs[index].style.outline =
                index >= s && index <= e ? '4px solid #cbd3fe' : 'none'
            }
          }

          _ec(v)
        }

        invert.callback = v => {
          selectImages()
        }

        try {
        } catch (error) {}
      }
    }

    if (
      nodeData?.name == 'VideoCombine_Adv' ||
      nodeData?.name == 'CombineAudioVideo'
    ) {
      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        const prefix = 'vhs_gif_preview_'
        const r = onExecuted ? onExecuted.apply(this, message) : undefined

        if (!this.widgets) this.widgets = []

        if (this.widgets) {
          const pos = this.widgets.findIndex(w => w.name === `${prefix}_0`)
          if (pos !== -1) {
            for (let i = pos; i < this.widgets.length; i++) {
              this.widgets[i].onRemoved?.()
            }
            this.widgets.length = pos
          }
          if (message?.gifs) {
            message.gifs.forEach((params, i) => {
              const previewUrl = api.apiURL(
                '/view?' + new URLSearchParams(params).toString()
              )
              const w = this.addCustomWidget(
                createPreviewElement(
                  `${prefix}_${i}`,
                  previewUrl,
                  params.format || 'image/gif'
                )
              )
              console.log(w)
              w.parent = this
            })
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
