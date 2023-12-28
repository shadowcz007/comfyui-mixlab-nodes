import { app } from '../../../scripts/app.js'
// import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

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
              console.log('this.inputs', this.inputs)
              let topLinkId = this.inputs[0].link
              let topNodeId = app.graph.links[topLinkId].origin_id
              let topIm = app.graph.getNodeById(topNodeId).imgs[0]

              let linkId = this.inputs[3].link
              let nodeId = app.graph.links[linkId].origin_id
              // console.log(linkId,this.inputs)
              let im = app.graph.getNodeById(nodeId).imgs[0]
              // let src = im.src
              setArea(
                im.naturalWidth,
                im.naturalHeight,
                topIm.src,
                im.src,
                data,
                updateValue
              )
            } catch (error) {}
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
