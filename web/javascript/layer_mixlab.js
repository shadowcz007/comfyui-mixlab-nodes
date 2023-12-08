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
    if(!svgElement)return
    // 获取SVG中 rect元素
    var rectElements = svgElement?.querySelectorAll('rect')||[]
  
    // 定义一个数组来存储处理后的数据
    var data = []
  
    Array.from(rectElements, (rectElement, i) => {
      // 获取rect元素的属性值
      var x = rectElement.getAttribute('x')
      var y = rectElement.getAttribute('y')
      var width = rectElement.getAttribute('width')
      var height = rectElement.getAttribute('height')
      if (x != undefined && y != undefined) {
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
          type: 'base64'
        }
  
        // 将处理后的数据添加到数组中
        data.push(rectData)
      }
    })
  
    var svgWidth = svgElement.getAttribute('width')
    var svgHeight = svgElement.getAttribute('height')
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
      type: 'base64'
    }
    data.push(rectData)
  
    // 打印处理后的数据
    console.log({ data, image: base64, svgElement })
    return { data, image: base64, svgElement }
  }

  
app.registerExtension({
  name: 'Mixlab.layer.EditLayer',
  //   async getCustomWidgets (app) {
  //     return {
  //         LAYER (node, inputName, inputData, app) {
  //         console.log('EditLayer##node', node,inputName, inputData)
  //         const widget = {
  //           type: inputData[0], // the type, CHEESE
  //           name: inputName, // the name, slice
  //           size: [128, 32], // a default size
  //           draw (ctx, node, width, y) {},
  //           computeSize (...args) {
  //             return [128, 32] // a method to compute the current size of the widget
  //           },
  //           async serializeValue (nodeId, widgetIndex) {
  //             // let d = getLocalData('_mixlab_svg_image')
  //             // const { data, image } = (await parseSvg(d[node.id]))||{}
  //             // console.log(data, image)
  //             // return JSON.parse(JSON.stringify({ data, image }))
  //             return []
  //           }
  //         }
  //         //  widget.something = something;          // maybe adds stuff to it
  //         node.addCustomWidget(widget) // adds it to the node
  //         return widget // and returns it.
  //       }
  //     }
  //   },

  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'EditLayer') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = async function () {
        orig_nodeCreated?.apply(this, arguments)

       

        const linkId = this.inputs.filter(ip => ip.name === 'layers')[0].link

        const nodeId = app.graph.links.filter(link => link.id == linkId)[0]?.origin_id

        let d = getLocalData('_mixlab_svg_image')
        const { data, image } = (await parseSvg(d[nodeId])) || {}
       
        let editIndex = 0

        let layer = data[editIndex]

        const updateValue = name => {
          const x = this.widgets.filter(w => w.name == name)[0]
          x.value = layer[name]
        }

        Array.from(['x', 'y', 'width', 'height', 'z_index'], n =>
          updateValue(n)
        )
 
        console.log('EditLayer nodeData', this.widgets, this.inputs,layer)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {  
          return onRemoved?.()
        }

        this.serialize_widgets = false //需要保存参数
      }

      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        const r = onExecuted?.apply?.(this, arguments)
        console.log('EditLayer executed', message)
        const { image_path } = message
        if (image_path) {
        }
        return r
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
