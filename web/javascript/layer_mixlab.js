import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

function downloadJsonFile (jsonData, fileName = 'grid.json') {
  const dataString = JSON.stringify(jsonData)
  const blob = new Blob([dataString], { type: 'application/json' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()

  // 释放URL对象
  setTimeout(() => {
    URL.revokeObjectURL(url)
  }, 0)
}

function createSelectWithOptions (options) {
  const select = document.createElement('select')

  options.forEach(option => {
    const optionElement = document.createElement('option')
    optionElement.text = option
    optionElement.value = option
    select.appendChild(optionElement)
  })

  select.style = `cursor: pointer;
  font-weight: 300; 
  height: 30px;
  min-width: 122px;
  position: absolute;
  top: 24px;
  left: 88px;
  z-index: 999999999999999;
       `

  return select
}

function drawCanvasWithText (w, h, tag, color = 'rgba(255,255,255,0.4)') {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')

  // 设置画布大小
  canvas.width = w
  canvas.height = h

  // 绘制白色背景
  ctx.fillStyle = color
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // 绘制文字
  ctx.fillStyle = '#000000'
  ctx.font = '20px Arial'
  ctx.fillText(tag, 50, 50)

  // 导出为Base64
  const base64 = canvas.toDataURL()

  return base64
}

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
    // flexDirection: 'column',
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

function createImage (url) {
  let im = new Image()
  return new Promise((res, rej) => {
    im.onload = () => res(im)
    im.src = url
  })
}

const parseSvg = async svgContent => {
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

function findImages (nodeId) {
  // 检查当前节点是否有 imgs 字段
  const n = app.graph.getNodeById(nodeId)
  if (n.imgs) {
    return n.imgs
  }

  // 检查当前节点的 inputs 是否有 image 字段
  if (n.inputs) {
    for (let i = 0; i < n.inputs.length; i++) {
      if (n.inputs[i].name === 'image' || n.inputs[i].name === 'images') {
        // 获取新的 nodeId，并递归调用 findImages 函数
        var linkId = n.inputs[i]?.link
        var origin_id = app.graph.links[linkId].origin_id
        return findImages(origin_id)
      }
    }
  }

  // 如果没有找到 imgs 字段或者 image 字段，则返回 null
  return null
}

async function setArea (cw, ch, topBase64, base64, data, fn) {
  let displayHeight = Math.round(window.screen.availHeight * 0.8)
  let div = document.createElement('div')
  div.innerHTML = `
    <div id='ml_overlay' style='position: absolute;top:0;background: #251f1fc4;
    height: 100vh;
    z-index:999999;
    width: 100%;'>
      <img id='ml_video' style='position: absolute; 
      height: ${displayHeight}px;user-select: none; 
      -webkit-user-drag: none;
      outline: 2px solid #eaeaea;
      box-shadow: 8px 9px 17px #575757;' />
      <div id='ml_selection' style='position: absolute; 
      border: 2px dashed red;
      pointer-events: none;
      background-image: url("${topBase64}");
            background-repeat: no-repeat;
            background-size: cover;
            '></div>
      <div class="mx_close"> X </div>
    </div>`
  // document.body.querySelector('#ml_overlay')
  document.body.appendChild(div)

  // let canvas = document.createElement('canvas')
  // canvas.width = cw
  // canvas.height = ch

  let img = div.querySelector('#ml_video')
  // let overlay = div.querySelector('#ml_overlay')
  let selection = div.querySelector('#ml_selection')
  let close = div.querySelector('.mx_close')
  let startX, startY, endX, endY
  let start = false
  let setDone = false
  // Set video source
  img.src = base64
  // canvas.toDataURL();
  close.style = `cursor: pointer;
  position: fixed;
  left: 12px;
  top: 12px;
  z-index: 99999999;
  background: black;
  width: 44px;
  height: 44px;
  text-align: center;
  line-height: 44px;`

  // init area
  // const data = getSetAreaData()
  let x = 0,
    y = 0,
    width = (cw * displayHeight) / ch,
    height = displayHeight

  let imgWidth = cw
  let imgHeight = ch

  if (data && data.width > 0 && data.height > 0) {
    // 相同尺寸窗口，恢复选区
    x = (width * data.x) / imgWidth
    y = (height * data.y) / imgHeight
    width = (width * data.width) / imgWidth
    height = (height * data.height) / imgHeight
  }

  selection.style.left = x + 'px'
  selection.style.top = y + 'px'
  selection.style.width = width + 'px'
  selection.style.height = height + 'px'

  // Add mouse events
  img.addEventListener('mousedown', startSelection)
  img.addEventListener('mousemove', updateSelection)
  img.addEventListener('mouseup', endSelection)

  const removeDiv = () => {
    div.remove()
    close.removeEventListener('click', removeDiv)
    img.removeEventListener('mousedown', startSelection)
    img.removeEventListener('mousemove', updateSelection)
    img.removeEventListener('mouseup', endSelection)
    img.removeEventListener('mousedown', setDoneCheck)
  }
  close.addEventListener('click', removeDiv)

  const setDoneCheck = event => {
    console.log(setDone)
    if (setDone) {
      img.addEventListener('mousedown', startSelection)
      img.addEventListener('mousemove', updateSelection)
      img.addEventListener('mouseup', endSelection)
      setDone = false
      start = false
      startX = event.clientX
      startY = event.clientY
    }
  }
  img.addEventListener('mousedown', setDoneCheck)

  function remove () {
    img.removeEventListener('mousedown', startSelection)
    img.removeEventListener('mousemove', updateSelection)
    img.removeEventListener('mouseup', endSelection)
    setDone = true
    // div.remove()
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

    startX = realStartX
    startY = realStartY
    endX = realEndX
    endY = realEndY
    // Calculate width, height, and coordinates
    let width = Math.round(Math.abs(endX - startX))
    let height = Math.round(Math.abs(endY - startY))
    let left = Math.round(Math.min(startX, endX))
    let top = Math.round(Math.min(startY, endY))

    if (width <= 0 && height <= 0) return remove()

    if (fn) fn(left, top, width, height)

    remove()
  }
}

async function setAreaTags (cw, ch, grids, fn) {
  let base64 = drawCanvasWithText(cw, ch, '', 'white')
  let displayHeight = Math.round(window.screen.availHeight * 0.8)
  let div = document.createElement('div')
  div.innerHTML = `
    <div id='ml_overlay' style='position: absolute;top:0;background: #251f1fc4;
    height: 100vh;
    z-index:999999;
    width: 100%;'>
      <img id='ml_video' style='position: absolute; 
      height: ${displayHeight}px;user-select: none; 
      -webkit-user-drag: none;
      outline: 2px solid #eaeaea;
      box-shadow: 8px 9px 17px #575757;' />
      ${Array.from(grids, g => {
        const { label: tag, grid } = g
        const [dx, dy, dw, dh] = grid
        const base64Data = drawCanvasWithText(dw, dh, tag)

        let x = 0,
          y = 0,
          width = (cw * displayHeight) / ch,
          height = displayHeight

        let imgWidth = cw
        let imgHeight = ch

        if (dw > 0 && dh > 0) {
          // 相同尺寸窗口，恢复选区
          x = (width * dx) / imgWidth
          y = (height * dy) / imgHeight
          width = (width * dw) / imgWidth
          height = (height * dh) / imgHeight
        }

        return `<div class='ml_selection' 
          data-tag="${tag}"
          style='position:absolute; 
          border: 2px dashed red;
          pointer-events: none;
          background-image: url("${base64Data}");
                background-repeat: no-repeat;
                background-size: cover;
                left:${x}px;
                top:${y}px;
                width:${width}px;
                height:${height}px;
                '></div>`
      })}
      <div class="mx_close"> X </div>
    </div>`
  // document.body.querySelector('#ml_overlay')
  document.body.appendChild(div)

  const tags = Array.from(grids, g => g.label)
  let select = createSelectWithOptions(tags)
  document.body.appendChild(select)

  let img = div.querySelector('#ml_video')
  // let overlay = div.querySelector('#ml_overlay')
  let selections = [...div.querySelectorAll('.ml_selection')]

  let selection = selections.filter(
    s => s.getAttribute('data-tag') === select.value
  )[0]

  select.addEventListener('change', e => {
    selection = selections.filter(
      s => s.getAttribute('data-tag') === select.value
    )[0]
  })

  // console.log(select.value,selection)
  let close = div.querySelector('.mx_close')
  let startX, startY, endX, endY
  let start = false
  let setDone = false
  // Set video source
  img.src = base64
  // canvas.toDataURL();
  close.style = `cursor: pointer;
  position: fixed;
  left: 12px;
  top: 12px;
  z-index: 99999999;
  background: black;
  width: 44px;
  height: 44px;
  text-align: center;
  line-height: 44px;`

  // Add mouse events
  img.addEventListener('mousedown', startSelection)
  img.addEventListener('mousemove', updateSelection)
  img.addEventListener('mouseup', endSelection)

  const removeDiv = () => {
    div.remove()
    select?.remove()
    close.removeEventListener('click', removeDiv)
    img.removeEventListener('mousedown', startSelection)
    img.removeEventListener('mousemove', updateSelection)
    img.removeEventListener('mouseup', endSelection)
    img.removeEventListener('mousedown', setDoneCheck)
  }
  close.addEventListener('click', removeDiv)

  const setDoneCheck = event => {
    console.log(setDone)
    if (setDone) {
      img.addEventListener('mousedown', startSelection)
      img.addEventListener('mousemove', updateSelection)
      img.addEventListener('mouseup', endSelection)
      setDone = false
      start = false
      startX = event.clientX
      startY = event.clientY
    }
  }
  img.addEventListener('mousedown', setDoneCheck)

  function remove () {
    img.removeEventListener('mousedown', startSelection)
    img.removeEventListener('mousemove', updateSelection)
    img.removeEventListener('mouseup', endSelection)
    setDone = true
    // select?.remove()
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

    startX = realStartX
    startY = realStartY
    endX = realEndX
    endY = realEndY
    // Calculate width, height, and coordinates
    let width = Math.round(Math.abs(endX - startX))
    let height = Math.round(Math.abs(endY - startY))
    let left = Math.round(Math.min(startX, endX))
    let top = Math.round(Math.min(startY, endY))

    if (width <= 0 && height <= 0) return remove()

    if (!!fn) fn(select.value, left, top, width, height)

    remove()
  }
}

app.registerExtension({
  name: 'Mixlab.layer.ShowLayer',
  async getCustomWidgets (app) {
    return {
      EDIT (node, inputName, inputData, app) {
        //   console.log('EditLayer##node', node,inputName, inputData)
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 44], // a default size
          draw (ctx, node, widget_width, y, widget_height) {
            // console.log('EditLayer', this)
            if (this.input)
              Object.assign(
                this.input.style,
                get_position_style(ctx, widget_width, 32, node.size[1])
              )
          },
          computeSize (...args) {
            return [128, 44] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            let d = getLocalData('_mixlab_edit_layer')
            // console.log('EditLayer',d[node.id])
            return d[node.id]
          }
        }
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      }
    }
  },

  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'ShowLayer') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = async function () {
        orig_nodeCreated?.apply(this, arguments)

        const findNode = nodeId => {
          let node = app.graph._nodes_by_id[nodeId]
          if (node?.type == 'Reroute') {
            let linkId = node.inputs.filter(i => i.type == '*')[0].link
            nodeId = app.graph.links.filter(link => link.id == linkId)[0]
              ?.origin_id
            return findNode(nodeId)
          } else {
            return nodeId
          }
        }

        // 获取layers数据
        const getLayers = async () => {
          console.log(
            'getLayers1',
            this.inputs.filter(ip => ip.name === 'layers')
          )
          let linkId = this.inputs.filter(ip => ip.name === 'layers')[0].link
          let nodeId = app.graph.links?.filter(link => link.id == linkId)[0]
            ?.origin_id

          if (nodeId) {
            nodeId = findNode(nodeId)
          }

          //   let node = app.graph._nodes_by_id[nodeId]
          //   if (node?.type == 'Reroute') {
          //     linkId = node.inputs[0].link
          //     nodeId = app.graph.links.filter(link => link.id == linkId)[0]
          //       ?.origin_id
          //   }

          let d = getLocalData('_mixlab_svg_image')
          console.log('test', d[nodeId])

          if (d[nodeId]) {
            let url = d[nodeId]
            let dt = await fetch(url)

            let svgStr = await dt.text()

            const { data } = (await parseSvg(svgStr)) || {}
            console.log('fetch', data)
            return data
          } else {
            return []
          }
        }

        // 修改layers数据
        const setLayer = async (editIndex, layers = null) => {
          //   let editIndex = 0
          let lys = layers || (await getLayers())
          let layer = lys[editIndex]
          //   console.log(layer)

          const updateValue = name => {
            const x = this.widgets.filter(w => w.name == name)[0]
            x.value = layer[name]
          }
          if (layer) {
            Array.from(['x', 'y', 'width', 'height', 'z_index'], n =>
              updateValue(n)
            )
          }
        }

        let that = this
        const save_edit_layer_index = i => {
          let data = getLocalData('_mixlab_edit_layer')
          data[that.id] = i
          localStorage.setItem('_mixlab_edit_layer', JSON.stringify(data))
        }

        await setLayer(0)
        save_edit_layer_index(0)

        const edit = this.widgets.filter(w => w.name == 'edit')[0]

        edit.input = $el('div', {})
        edit.input.style = `
        display: flex;
        flex-direction:row;
        align-items: center;
        margin-top: 0;`

        const ip = $el('input', {})
        ip.className = 'comfy-multiline-input'
        ip.type = 'number'
        ip.min = 0
        ip.step = 1
        ip.max = Math.max(0, (await getLayers()).length - 1)
        // ip.className = `${'comfy-multiline-input'} `

        ip.value = 0

        ip.style = `
        background-color: var(--comfy-input-bg);
        color: var(--input-text);
        outline: none;
          border: none;
          padding: 4px;
          width: 60%;
          cursor: pointer;
          height: 24px;`
        const label = document.createElement('label')
        label.style = 'font-size: 10px;min-width:32px'
        label.innerText = 'Layer Index'
        edit.input.appendChild(label)
        edit.input.appendChild(ip)

        document.body.appendChild(edit.input)

        ip.addEventListener('click', async event => {
          console.log(await getLayers())
          ip.max = Math.max(0, (await getLayers()).length - 1)
        })

        ip.addEventListener('change', async event => {
          let index = ~~ip.value
          let lys = await getLayers()
          await setLayer(index, lys)
          app.graph.setDirtyCanvas(true, true)
          save_edit_layer_index(index)
        })

        // console.log('EditLayer nodeData', edit)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          edit.input.remove()
          return onRemoved?.()
        }

        if (this.onResize) {
          this.onResize(this.size)
        }

        this.serialize_widgets = false //需要保存参数
      }
    }
  },
  async loadedGraphNode (node, app) {
    // Fires every time a node is constructed
    // You can modify widgets/add handlers/etc here
    if (node.type === 'SvgImage') {
      let widget = node.widgets.filter(w => w.div)[0]
      let data = getLocalData('_mixlab_svg_image')
      let id = node.id

      // widget.div.querySelector('.Svg').value = data[id] || '#000000'
    }
  }
})

app.registerExtension({
  name: 'Mixlab.layer.NewLayer',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeData.name === 'NewLayer') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = async function () {
        orig_nodeCreated?.apply(this, arguments)

        let b = this.widgets.filter(w => w.type === 'button')[0]
        // const [w, h, base64] = canvas

        if (!b) {
          const updateValue = (x1, y1, w1, h1) => {
            if (this.widgets) {
              for (const widget of this.widgets) {
                if (widget.name === 'x') {
                  widget.value = x1
                }
                if (widget.name === 'y') {
                  widget.value = y1
                }
                if (widget.name === 'width') {
                  widget.value = w1
                }
                if (widget.name === 'height') {
                  widget.value = h1
                }
              }
            }
          }

          this.addWidget('button', 'Set Area', '', () => {
            let data = {}
            for (const widget of this.widgets) {
              if (widget.name === 'x') {
                data.x = widget.value
              }
              if (widget.name === 'y') {
                data.y = widget.value
              }
              if (widget.name === 'width') {
                data.width = widget.value
              }
              if (widget.name === 'height') {
                data.height = widget.value
              }
            }
            try {
              console.log('this.inputs', this.id)
              let imgs = findImages(this.id)

              // let topLinkId = this.inputs[0].link
              // let topNodeId = app.graph.links[topLinkId].origin_id
              let topIm = imgs[0]

              let linkId = this.inputs[3].link
              let nodeId = app.graph.links[linkId].origin_id
              // console.log(linkId,this.inputs)
              let imgs2 = findImages(nodeId)
              let im = imgs2[0]
              console.log(topIm, im)
              // let src = im.src
              setArea(
                im.naturalWidth,
                im.naturalHeight,
                topIm.src,
                im.src,
                data,
                updateValue
              )
            } catch (error) {
              console.log(error)
            }
          })
        }
      }

      const onRemoved = this.onRemoved
      this.onRemoved = () => {
        // let b = this.widgets.filter(w => w.type === 'button')[0];

        return onRemoved?.()
      }

      if (this.onResize) {
        this.onResize(this.size)
      }

      this.serialize_widgets = true //需要保存参数
    }
  }
})

app.registerExtension({
  name: 'Mixlab.layer.GridInput',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'GridInput') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = async function () {
        orig_nodeCreated?.apply(this, arguments)

        const grids_widget = this.widgets.filter(w => w.name == 'grids')[0]

        const widget = {
          type: 'div',
          name: 'upload',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, y, node.size[1]),
              {
                justifyContent: 'flex-start'
              }
            )
          }
        }

        widget.div = $el('div', {})

        const addBtn = document.createElement('button')
        addBtn.innerText = 'Add Box'
        addBtn.style = `cursor: pointer;
        font-weight: 300;
        margin: 2px; 
        color: var(--descrip-text);
        background-color: var(--comfy-input-bg);
        border-radius: 8px;
        border-color: var(--border-color);
        border-style: solid;height: 30px;min-width: 122px;
       `

        const vbtn = document.createElement('button')
        vbtn.innerText = 'Set Box'
        vbtn.style = `cursor: pointer;
        font-weight: 300;
        margin: 2px; 
        color: var(--descrip-text);
        background-color: var(--comfy-input-bg);
        border-radius: 8px;
        border-color: var(--border-color);
        border-style: solid;height: 30px;min-width: 122px;
       `

        const btn = document.createElement('button')
        btn.innerText = 'Upload JSON'

        btn.style = `cursor: pointer;
        font-weight: 300;
        margin: 2px; 
        color: var(--descrip-text);
        background-color: var(--comfy-input-bg);
        border-radius: 8px;
        border-color: var(--border-color);
        border-style: solid;height: 30px;min-width: 122px;
       `

        addBtn.addEventListener('click', () => {
          const { width, height, grids } = JSON.parse(grids_widget.value)
          grids.push({
            label: 'background',
            grid: [12, 12, width - 24, height - 24]
          })
          grids_widget.value = JSON.stringify(
            {
              width,
              height,
              grids
            },
            null,
            2
          )
        })

        vbtn.addEventListener('click', () => {
          const { width, height, grids } = JSON.parse(grids_widget.value)

          setAreaTags(width, height, grids, (tag, x, y, w, h) => {
            grids_widget.value = JSON.stringify(
              {
                width,
                height,
                grids: Array.from(grids, g => {
                  if (g.label === tag) {
                    g.grid = [x, y, w, h]
                  }
                  return g
                })
              },
              null,
              2
            )
          })
        })

        btn.addEventListener('click', () => {
          let inp = document.createElement('input')
          inp.type = 'file'
          inp.accept = '.json'
          inp.click()
          inp.addEventListener('change', event => {
            // 获取选择的文件
            const file = event.target.files[0]
            this.title = file.name.split('.')[0]

            // console.log(file.name.split('.')[0])
            // 创建文件读取器
            const reader = new FileReader()

            // 定义读取完成事件的回调函数
            reader.onload = event => {
              // 读取完成后的文本内容
              const fileContent = JSON.parse(event.target.result)
              const grids = fileContent
              grids_widget.value = JSON.stringify(grids, null, 2)
              // widget.value = grids

              inp.remove()
            }

            // 以文本方式读取文件
            reader.readAsText(file)
          })
        })

        widget.div.appendChild(addBtn)
        widget.div.appendChild(vbtn)
        widget.div.appendChild(btn)
        document.body.appendChild(widget.div)
        this.addCustomWidget(widget)

        const onExecuted = nodeType.prototype.onExecuted
        nodeType.prototype.onExecuted = function (message) {
          const r = onExecuted?.apply?.(this, arguments)

          let json = message.json
          if (json) {
            json = {
              width: json[0],
              height: json[1],
              grids: json[2]
            }
            grids_widget.value = JSON.stringify(json, null, 2)
            // widget.value = json
          }

          return r
        }

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
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
    if (node.type === 'GridInput') {
      try {
        const grids_widget = node.widgets.filter(w => w.name == 'grids')[0]
        const { width, height, grids } = JSON.parse(grids_widget.value)
        console.log('#GridInput', node, grids)

        const div = node.widgets.filter(w => w.name == 'upload')[0]
        div.div.querySelector('select').innerHTML = Array.from(
          grids,
          g => `<option value="${g.label}">${g.label}</option>`
        ).join('')
      } catch (error) {}
    }
  }
})

app.registerExtension({
  name: 'Mixlab.layer.GridDisplayAndSave',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'GridDisplayAndSave') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = async function () {
        orig_nodeCreated?.apply(this, arguments)

        const grids_widget = this.widgets.filter(w => w.name == 'grids')[0]
        console.log('GridDisplayAndSave', grids_widget)
        const widget = {
          type: 'div',
          name: 'save_json',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, y, node.size[1]),
              {
                justifyContent: 'flex-start',
                flexDirection: 'column'
              }
            )
          }
        }

        widget.div = $el('div', {})

        const btn = document.createElement('button')
        btn.innerText = 'Save JSON'

        btn.style = `cursor: pointer;
        font-weight: 300;
        margin: 2px; 
        color: var(--descrip-text);
        background-color: var(--comfy-input-bg);
        border-radius: 8px;
        border-color: var(--border-color);
        border-style: solid;height: 30px;min-width: 122px;
        max-width: 122px;
       `

        btn.addEventListener('click', () => {
          if (window._mixlab_grid)
            downloadJsonFile(
              window._mixlab_grid,
              this.widgets.filter(w => w.name == 'filename_prefix')[0]?.value +
                '_grid.json'
            )
        })

        widget.div.appendChild(btn)
        document.body.appendChild(widget.div)
        this.addCustomWidget(widget)

        const onExecuted = nodeType.prototype.onExecuted
        nodeType.prototype.onExecuted = function (message) {
          const r = onExecuted?.apply?.(this, arguments)
          let save_json = this.widgets.filter(d => d.name == 'save_json')[0]
          let div = save_json?.div
          // console.log('Test',message)

          let image = message.image[0]
          let json = message.json
          if (image) {
            const { filename, subfolder, type } = image

            if (!div.querySelector('img')) {
              let im = new Image()
              div.appendChild(im)
              im.style.width = '100%'
            }
            div.querySelector('img').src = api.apiURL(
              `/view?filename=${encodeURIComponent(
                filename
              )}&type=${type}&subfolder=${subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`
            )

            window._mixlab_grid = {
              width: json[0],
              height: json[1],
              grids: json[2]
            }
            // console.log(src)
          }

          this.onResize?.(this.size)

          return r
        }

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
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
    if (node.type === 'GridDisplayAndSave') {
      try {
        let grids_widget = node.widgets.filter(w => w.name === 'grids')[0]
        // let ks = getLocalData(`_mixlab_PromptSlide`)
        let uploadWidget = node.widgets.filter(w => w.name == 'upload')[0]
        // console.log('##widget', uploadWidget.value)
        let grids = JSON.parse(uploadWidget.value)
      } catch (error) {}
    }
  }
})
