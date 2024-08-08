import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { $el } from '../../../scripts/ui.js'

function base64ToBlobFromURL (base64URL, contentType) {
  return fetch(base64URL).then(response => response.blob())
}

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
  // let src = api.apiURL(
  //   `/view?filename=${encodeURIComponent(
  //     name
  //   )}&type=input&subfolder=${subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`
  // )

  return data
}
// 上传得到url
async function uploadBase64ToFile (base64) {
  let bg_blob = await base64ToBlobFromURL(base64)
  let url = await uploadImage(bg_blob, '.png')
  return url
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
    flexDirection: 'column',
    // alignItems: 'center',
    justifyContent: 'space-around'
  }
}

const p5InputNode = {
  name: 'Mixlab.Comfy.P5Input',
  async getCustomWidgets (app) {
    return {
      IMAGEBASE64 (node, inputName, inputData, app) {
        const widget = {
          value: {
            images: []
          }, // 不能[x,x,x]
          type: inputData[0], // the type
          name: inputName, // the name, slice
          size: [320, 120], // a default size
          draw (ctx, node, width, y) {},
          computeSize (...args) {
            return [128, 32] // a method to compute the current size of the widget
          }
        }
        node.addCustomWidget(widget)
        return widget
      }
    }
  },

  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'P5Input') {
      // console.log('P5Input')
      const orig_nodeCreated = nodeType.prototype.onNodeCreated

      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)

        const widget = {
          type: 'div',
          name: 'image_base64',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width - 24, 44, node.size[1])
            )
          },
          serialize: false
        }

        widget.div = $el('div', {})

        widget.div.style = `margin:12px;width:400px;height:480px;background:white`

        document.body.appendChild(widget.div)

        this.addCustomWidget(widget)

        // document.addEventListener('wheel', handleMouseWheel)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          widget.div.remove()
          // window.removeEventListener('message', ms)
          return onRemoved?.()
        }

        // 节点的大小控制
        this.setSize([480, 560])
        app.canvas.draw(true, true)

        const onResize = this.onResize
        this.onResize = () => {
          // 设置最小尺寸
          if (
            Math.max(this.size[0], 480) != this.size[0] &&
            Math.max(this.size[1], 560) != this.size[1]
          ) {
            this.setSize([
              Math.max(this.size[0], 480),
              Math.max(this.size[1], 560)
            ])
          }

          return onResize?.apply(this, arguments)
        }

        this.serialize_widgets = true //需要保存参数
      }

      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        onExecuted?.apply(this, arguments)
        // console.log('##onExecuted', this, message._info)
        //   app.graph.getNodeById(8).widgets[1].div.querySelector('iframe').contentWindow.postMessage('Hello from parent', '*');
      }
    }
  },

  async loadedGraphNode (node, app) {
    if (node.type === 'P5Input') {
    }
  },
  nodeCreated (node, app) {
    //数据延迟？？
    setTimeout(() => {
      let widget = node.widgets?.filter(w => w.name == 'image_base64')[0]
      let framesWidget = node.widgets?.filter(w => w.name == 'frames')[0]
      if (node.type === 'P5Input' && widget) {
        if (framesWidget && !framesWidget.value)
          framesWidget.value = { images: [] }

        framesWidget.value._seed = Math.random()

        let nodeId = node.id
        //延迟才能获得this.id
        widget.div.innerHTML = `<iframe src="extensions/comfyui-mixlab-nodes/p5_export/p5.html?id=${nodeId}" 
          style="border:0;width:100%;height:100%;"
         ></iframe>`

        // 监听来自iframe的消息
        const ms = async event => {
          const data = event.data
          if (
            data.from === 'p5.widget' &&
            data.status === 'save' &&
            data.frames &&
            data.frames.length > 0 &&
            data.nodeId == nodeId
          ) {
            const frames = data.frames
            console.log(frames.length, nodeId)
            //workflow会存储到local，会卡死
            framesWidget.value.images = []
            for (const f of frames) {
              let file = await uploadBase64ToFile(f)
              framesWidget.value.images.push(file)
            }
            // framesWidget.value.base64 = frames
            framesWidget.value._seed = Math.random()
            node.title = 'P5 Input #' + frames.length
          }
        }
        window.addEventListener('message', ms)
      }
    }, 1000)
  }
}

app.registerExtension(p5InputNode)
