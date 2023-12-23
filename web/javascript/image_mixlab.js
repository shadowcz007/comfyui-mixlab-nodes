import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

async function uploadImage (blob, fileType = '.svg', filename) {
  // const blob = await (await fetch(src)).blob();
  const body = new FormData()
  body.append(
    'image',
    new File([blob], (filename || new Date().getTime()) + fileType)
  )

  const resp = await api.fetchApi('/upload/image', {
    method: 'POST',
    body
  })

  // console.log(resp)
  let data = await resp.json()
  let { name, subfolder } = data
  let src = api.apiURL(
    `/view?filename=${encodeURIComponent(
      name
    )}&type=input&subfolder=${subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`
  )

  return src
}

function base64ToBlobFromURL (base64URL, contentType) {
  return fetch(base64URL).then(response => response.blob())
}

function getContentTypeFromBase64 (base64Data) {
  const regex = /^data:(.+);base64,/
  const matches = base64Data.match(regex)
  if (matches && matches.length >= 2) {
    return matches[1]
  }
  return null
}

// 示例用法
// const base64Data = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAAAAAD/...'; // 替换为实际的base64图片数据
// const contentType = getContentTypeFromBase64(base64Data);
// console.log(contentType);

// // 示例用法
// const base64Data = '...'; // 替换为实际的base64图片数据
// const contentType = 'image/jpeg'; // 替换为实际的图片类型

// const blob = base64ToBlob(base64Data, contentType);
// console.log(blob);

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
    // height: `${node_height * 0.3 - MARGIN * 2}px`,
    // background: '#EEEEEE',
    display: 'flex',
    flexDirection: 'column',
    // alignItems: 'center',
    justifyContent: 'space-around'
  }
}

const getLocalData = key => {
  let data = {}
  try {
    data = JSON.parse(localStorage.getItem(key)) || {}
  } catch (error) {
    return {}
  }
  return data
}

const setLocalDataOfWin = (key, value) => {
  localStorage.setItem(key, JSON.stringify(value))
  // window[key] = value
}

function createImage (url) {
  let im = new Image()
  return new Promise((res, rej) => {
    im.onload = () => res(im)
    im.src = url
  })
}

const parseImage = url => {
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

const parseSvg = async svgContent => {
  let scale = 2
  // 创建一个临时的DOM元素来解析SVG
  const tempContainer = document.createElement('div')
  tempContainer.innerHTML = svgContent

  // 提取SVG元素
  const svgElement = tempContainer.querySelector('svg')
  if (!svgElement) return
  // 获取SVG中 rect元素
  var rectElements = svgElement?.querySelectorAll('rect') || []
  // console.log(rectElements,svgElement)
  // 定义一个数组来存储处理后的数据
  var data = []

  Array.from(rectElements, (rectElement, i) => {
    // 获取rect元素的属性值
    var x = ~~(rectElement.getAttribute('x') || 0)
    var y = ~~(rectElement.getAttribute('y') || 0)
    var width = ~~rectElement.getAttribute('width')
    var height = ~~rectElement.getAttribute('height')
    // console.log('rectElements',rectElement,x,y,width,height)
    if (x != undefined && y != undefined && width && height) {
      // 创建一个新的canvas元素
      var canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      var context = canvas.getContext('2d')

      // 填充颜色到canvas
      var fill = rectElement.getAttribute('fill')
      context.fillStyle = fill
      context.fillRect(0, 0, width, height)

      // 将canvas转换为base64格式
      var base64 = canvas.toDataURL()

      // 将数据转化为指定的JSON格式

      var rectData = {
        x: parseInt(x),
        y: parseInt(y),
        width: parseInt(width),
        height: parseInt(height),
        z_index: i + 1,
        scale_option: 'width',
        image: base64,
        mask: base64,
        type: 'base64',
        _t: 'rect'
      }

      // 将处理后的数据添加到数组中
      data.push(rectData)
    }
  })

  var svgWidth = svgElement.getAttribute('width')
  var svgHeight = svgElement.getAttribute('height')

  if (!(svgWidth && svgHeight)) {
    // viewBox
    let viewBox = svgElement.viewBox.baseVal

    svgWidth = viewBox.width
    svgHeight = viewBox.height
  } else {
    try {
      svgWidth = ~~svgWidth.replace('px', '')
      svgHeight = ~~svgHeight.replace('px', '')
    } catch (error) {}
  }

  // 创建一个新的canvas元素
  var canvas = document.createElement('canvas')
  canvas.width = svgWidth
  canvas.height = svgHeight
  var context = canvas.getContext('2d')
  // 绘制SVG到canvas
  var svgString = new XMLSerializer().serializeToString(svgElement)
  var DOMURL = window.URL || window.webkitURL || window

  var svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
  var url = DOMURL.createObjectURL(svgBlob)

  let img = await createImage(url)
  context.drawImage(img, 0, 0)

  let base64 = canvas.toDataURL()

  var rectData = {
    x: 0,
    y: 0,
    width: parseInt(svgWidth),
    height: parseInt(svgHeight),
    z_index: 0,
    scale_option: 'width',
    image: base64,
    mask: base64,
    type: 'base64',
    _t: 'canvas'
  }
  data.push(rectData)

  // 打印处理后的数据
  console.log('layers', { data, image: base64, svgElement })
  return { data, image: base64, svgElement }
}

function exportModelViewerImage (
  modelViewer,
  width,
  height,
  format = 'image/png',
  quality = 1.0
) {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')

  return new Promise((resolve, reject) => {
    context.drawImage(modelViewer, 0, 0, width, height)

    resolve(canvas.toDataURL(format, quality))
  })
}

app.registerExtension({
  name: 'Mixlab.image.SvgImage',
  async getCustomWidgets (app) {
    return {
      SVG (node, inputName, inputData, app) {
        // console.log('##node', node, inputName, inputData)
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 88], // a default size
          draw (ctx, node, width, y) {},
          computeSize (...args) {
            return [128, 88] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            let d = getLocalData('_mixlab_svg_image')
            // console.log('serializeValue',d)
            if (d) {
              let url = d[node.id]
              let dt = await fetch(url)
              let svgStr = await dt.text()
              const { data, image } = (await parseSvg(svgStr)) || {}
              // console.log(data, image)
              return JSON.parse(JSON.stringify({ data, image }))
            } else {
              return
            }
          }
        }

        // console.log('##node',node.serialize)
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node

        return widget // and returns it.
      }
    }
  },

  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'SvgImage') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = async function () {
        orig_nodeCreated?.apply(this, arguments)

        const uploadWidget = this.widgets.filter(w => w.name == 'upload')[0]
        // console.log('SvgImage nodeData',await uploadWidget.serializeValue())

        const widget = {
          type: 'div',
          name: 'upload-preview',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, 44, node.size[1])
            )
          }
        }

        widget.div = $el('div', {})

        document.body.appendChild(widget.div)

        const inputDiv = (key, placeholder, svgContainer) => {
          let div = document.createElement('div')
          const ip = document.createElement('input')
          ip.type = 'file'
          ip.className = `${'comfy-multiline-input'} ${placeholder}`
          div.style = `display: flex;
          align-items: center; 
          margin: 6px 8px;
          margin-top: 0;`
          ip.placeholder = placeholder
          // ip.value = value

          ip.style = `outline: none;
          border: none;
          padding: 4px;
          width: 60%;cursor: pointer;
          height: 32px;`
          const label = document.createElement('label')
          label.style = 'font-size: 10px;min-width:32px'
          label.innerText = placeholder
          div.appendChild(label)
          div.appendChild(ip)

          let that = this

          ip.addEventListener('change', event => {
            const file = event.target.files[0]
            const reader = new FileReader()

            // 读取文件内容
            reader.onload = async e => {
              const svgContent = e.target.result

              var blob = new Blob([svgContent], { type: 'image/svg+xml' })
              let url = await uploadImage(blob)
              // console.log(url)
              const { svgElement, data, image } = await parseSvg(svgContent)
              // 将提取的SVG元素显示在页面上
              let dd = getLocalData(key)
              dd[that.id] = url
              setLocalDataOfWin(key, dd)
              // console.log(this.id, ip.value.trim())

              svgElement.style = `width: 90%;padding: 5%;height: auto;`
              // 将提取的SVG元素显示在页面上

              svgContainer.innerHTML = ''
              svgContainer.appendChild(svgElement)
              let h = ~~getComputedStyle(svgElement).height.replace('px', '')
              if (that.size && that.size[1] < h) {
                that.setSize([that.size[0], that.size[1] + h])
                app.canvas.draw(true, true)
              }
              // console.log(that.size,~~getComputedStyle(svgElement).height.replace('px',''))

              uploadWidget.value = await uploadWidget.serializeValue()
            }

            // 以文本形式读取文件
            reader.readAsText(file)
          })
          return div
        }

        let svg = document.createElement('div')
        svg.className = 'preview'
        svg.style = `background:#eee;margin-top: 12px;`

        let upload = inputDiv('_mixlab_svg_image', 'Svg', svg)

        widget.div.appendChild(upload)
        widget.div.appendChild(svg)
        this.addCustomWidget(widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          upload.remove()
          svg.remove()
          widget.div.remove()
          return onRemoved?.()
        }

        if (this.onResize) {
          this.onResize(this.size)
        }

        this.serialize_widgets = true //需要保存参数
      }
    }
  },
  async loadedGraphNode (node, app) {
    // Fires every time a node is constructed
    // You can modify widgets/add handlers/etc here
    const sleep = (t = 1000) => {
      return new Promise((res, rej) => {
        setTimeout(() => res(1), t)
      })
    }
    if (node.type === 'SvgImage') {
      // await sleep(0)
      let widget = node.widgets.filter(w => w.name === 'upload-preview')[0]

      let dd = getLocalData('_mixlab_svg_image')

      let id = node.id
      console.log('SvgImage load', node.widgets[0], node.widgets)
      if (!dd[id]) return
      let dt = await fetch(dd[id])
      let svgStr = await dt.text()

      const { svgElement, data, image } = await parseSvg(svgStr)
      svgElement.style = `width: 90%;padding: 5%;height:auto`
      // 将提取的SVG元素显示在页面上

      widget.div.querySelector('.preview').innerHTML = ''
      widget.div.querySelector('.preview').appendChild(svgElement)

      const uploadWidget = node.widgets.filter(w => w.name == 'upload')[0]
      uploadWidget.value = await uploadWidget.serializeValue()
    }
  }
})
