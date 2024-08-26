import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'

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

  return data
}

// 上传得到url
async function uploadBase64ToFile (base64) {
  let bg_blob = await base64ToBlobFromURL(base64)
  let url = await uploadImage(bg_blob, '.png')
  return url
}

class Visualizer {
  constructor (node, container, visualSrc) {
    this.node = node

    this.iframe = document.createElement('iframe')
    Object.assign(this.iframe, {
      scrolling: 'no',
      overflow: 'hidden'
    })
    this.iframe.src = '/mixlab/app/' + visualSrc + '.html'
    console.log('#Visualizer', container, this.iframe)
    container.appendChild(this.iframe)
  }

  updateVisual (params) {
    console.log('#updateVisual', params, this.iframe)
    // const iframeDocument = this.iframe.contentWindow.document
    // const previewScript = iframeDocument.getElementById('visualizer')
    // previewScript.setAttribute(
    //   'reference_image',
    //   JSON.stringify(params.reference_image)
    // )
    // previewScript.setAttribute('depth_map', JSON.stringify(params.depth_map))
    // Update the reference image and depth map
    this.iframe.contentWindow.postMessage(params, '*')
  }

  remove () {
    this.container.remove()
  }
}

function createVisualizer (node, inputName, typeName, inputData, app) {
  node.name = inputName

  const widget = {
    type: typeName,
    name: 'preview3d',
    callback: () => {},
    draw: function (ctx, node, widgetWidth, widgetY, widgetHeight) {
      const margin = 10
      const top_offset = 5
      const visible = app.canvas.ds.scale > 0.5 && this.type === typeName
      const w = widgetWidth - margin * 4
      const clientRectBound = ctx.canvas.getBoundingClientRect()
      const transform = new DOMMatrix()
        .scaleSelf(
          clientRectBound.width / ctx.canvas.width,
          clientRectBound.height / ctx.canvas.height
        )
        .multiplySelf(ctx.getTransform())
        .translateSelf(margin, margin + widgetY)

      Object.assign(this.visualizer.style, {
        left: `${transform.a * margin + transform.e + 40}px`,
        top: `${transform.d + transform.f + top_offset}px`,
        width: `${w * transform.a}px`,
        height: `${
          w * transform.d - widgetHeight - margin * 15 * transform.d
        }px`,
        position: 'absolute',
        overflow: 'hidden',
        zIndex: app.graph._nodes.indexOf(node)
      })

      Object.assign(this.visualizer.children[0].style, {
        transformOrigin: '50% 50%',
        width: '100%',
        height: '100%',
        border: '0 none'
      })

      this.visualizer.hidden = !visible
    }
  }

  const container = document.createElement('div')
  container.id = `Comfy3D_${inputName}`

  node.visualizer = new Visualizer(node, container, typeName)
  widget.visualizer = container
  widget.parent = node

  document.body.appendChild(widget.visualizer)

  node.addCustomWidget(widget)

  node.updateParameters = params => {
    // console.log('#updateParameters', params)
    params.id = node.id
    // node.visualizer = new Visualizer(node, container, typeName)
    node.visualizer.updateVisual(params)
  }

  // Events for drawing backgound
  node.onDrawBackground = function (ctx) {
    if (!this.flags.collapsed) {
      node.visualizer.iframe.hidden = false
    } else {
      node.visualizer.iframe.hidden = true
    }
  }

  // Make sure visualization iframe is always inside the node when resize the node
  node.onResize = function () {
    let [w, h] = this.size
    if (w <= 600) w = 600
    if (h <= 500) h = 500

    if (w > 600) {
      h = w - 100
    }

    this.size = [w, h]
  }

  // Events for remove nodes
  node.onRemoved = () => {
    for (let w in node.widgets) {
      if (node.widgets[w].visualizer) {
        node.widgets[w].visualizer.remove()
      }
    }
  }

  return {
    widget: widget
  }
}

function registerVisualizer (nodeType, nodeData, nodeClassName, typeName) {
  if (nodeData.name == nodeClassName) {
    const onNodeCreated = nodeType.prototype.onNodeCreated

    nodeType.prototype.onNodeCreated = async function () {
      const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined

      let Preview3DNode = app.graph._nodes.filter(
        wi => wi.type == nodeClassName
      )
      let nodeName = `Preview3DNode_${Preview3DNode.length}`

      const result = await createVisualizer.apply(this, [
        this,
        nodeName,
        typeName,
        {},
        app
      ])

      this.setSize([600, 500])

      return r
    }

    nodeType.prototype.onExecuted = async function (message) {
      // Check if reference image and depth map are available
      if (message.reference_image && message.depth_map) {
        const params = {}
        params.reference_image = message.reference_image[0]
        params.depth_map = message.depth_map[0]
        this.updateParameters(params)
      }
    }
  }
}

app.registerExtension({
  name: 'Mixlab.nodes.depthviewer',

  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    registerVisualizer(nodeType, nodeData, 'DepthViewer', 'threeVisualizer')
  },
  nodeCreated (node, app) {
    //数据延迟？？
    setTimeout(() => {
      let widget = node.widgets?.filter(w => w.name == 'preview3d')[0]
      let framesWidget = node.widgets?.filter(w => w.name == 'frames')[0]

      if (node.type === 'DepthViewer' && widget) {
        let nodeId = node.id
        //延迟才能获得this.id
        widget.visualizer.querySelector('iframe').src += '?id=' + nodeId
        // console.log('DepthViewer',widget)
        window.addEventListener('message', async event => {
          // 检查消息的来源，确保消息来自可信的源
          console.log(event)
          const { id, imgs } = event.data
          if (id == nodeId) {
            framesWidget.value = { images: [] }

            for (const f of imgs) {
              let file = await uploadBase64ToFile(f)
              framesWidget.value.images.push(file)
            }
            // framesWidget.value.base64 = frames
            framesWidget.value._seed = Math.random()
            node.title = 'Input #' + imgs.length
          }
        })
      }
    }, 1000)
  }
})
