import { app } from '../../../scripts/app.js'
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

const p5InputNode = {
  name: 'Mixlab.Comfy.P5Input',
  async getCustomWidgets (app) {
    return {
      IMAGEBASE64 (node, inputName, inputData, app) {
        const widget = {
          value: {
            base64: []
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
      console.log('P5Input')
      const orig_nodeCreated = nodeType.prototype.onNodeCreated

      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)

        let imagesWidget = this.widgets.filter(w => w.name == 'frames')[0]

        const widget = {
          type: 'div',
          name: 'image_base64',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width-24, 44, node.size[1])
            )
          },
          serialize: false
        }

        widget.div = $el('div', {})

        widget.div.style = `margin:12px;width:400px;height:480px;background:white`

        document.body.appendChild(widget.div)

       
        widget.div.innerHTML = `<iframe src="extensions/comfyui-mixlab-nodes/p5.html" 
         style="border:0;width:100%;height:100%;"
        ></iframe>`;

      
        // 如果是复制的，有数据 , 这个不生效，取不到数据， 需要在nodeCreated里获取
        // console.log('#LoadImagesToBatch', imagesWidget.value?.base64)

        const btn = document.createElement('button')
        btn.innerText = 'Upload Image'

        btn.style = `cursor: pointer;
          font-weight: 300;
          margin: 2px; 
          color: var(--descrip-text);
          background-color: var(--comfy-input-bg);
          border-radius: 8px;
          border-color: var(--border-color);
          border-style: solid;height: 30px;min-width: 122px;
         `

        btn.addEventListener('click', e => {
          e.preventDefault()
         
        })

        this.addCustomWidget(widget)

        // document.addEventListener('wheel', handleMouseWheel)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
        
          widget.div.remove()
          try {
            // document.removeEventListener('wheel', handleMouseWheel)
          } catch (error) {
            console.log(error)
          }

          return onRemoved?.()
        }

        this.serialize_widgets = true //需要保存参数
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
      // console.log('#LoadImagesToBatch', node.type)
      if (node.type === 'P5Input') {
      }
    }, 1000)
  }
}

app.registerExtension(p5InputNode)
