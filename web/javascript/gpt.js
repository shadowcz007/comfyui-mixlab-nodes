import { app } from '../../../scripts/app.js'
// import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

async function getConfig () {
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`

  const res = await fetch(`${url}/mixlab`, {
    method: 'POST'
  })
  return await res.json()
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

app.registerExtension({
  name: 'Mixlab.GPT.ChatGPT',
  async getCustomWidgets (app) {
    return {
      KEY (node, inputName, inputData, app) {
        // console.log('node', inputName, inputData[0])
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 24], // a default size
          draw (ctx, node, width, y) {},
          computeSize (...args) {
            return [128, 24] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            return localStorage.getItem('_mixlab_api_key') || ''
          }
        }
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      },
      URL (node, inputName, inputData, app) {
        // console.log('node', inputName, inputData[0])
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 24], // a default size
          draw (ctx, node, width, y) {
            // a method to draw the widget (ctx is a CanvasRenderingContext2D)
          },
          computeSize (...args) {
            return [128, 24] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            return localStorage.getItem('_mixlab_api_url') || ''
          }
        }
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      }
    }
  },
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    // console.log(nodeType.comfyClass)
    if (nodeType.comfyClass == 'ChatGPT') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)

        console.log('ChatGPT widtget', this.widgets)

        const api_key = this.widgets.filter(w => w.name == 'api_key')[0]
        const api_url = this.widgets.filter(w => w.name == 'api_url')[0]
        console.log('api_key', api_key, api_url)

        const widget = {
          type: 'div',
          name: 'chatgpt div',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, api_key.y, node.size[1])
            )
          }
        }

        widget.div = $el('div', {})

        document.body.appendChild(widget.div)

        const inputKey = document.createElement('input'),
          inputUrl = document.createElement('input')
        inputKey.type = 'text'
        inputUrl.type = 'text'

        inputKey.placeholder = 'Key'
        inputUrl.placeholder = 'URL'

        inputKey.style = `margin:4px 48px;`
        inputUrl.style = `margin:4px 48px`

        inputUrl.value = localStorage.getItem('_mixlab_api_url') || ''
        inputKey.value = localStorage.getItem('_mixlab_api_key') || ''

        widget.div.appendChild(inputKey)
        widget.div.appendChild(inputUrl)

        inputKey.addEventListener('change', () => {
          api_key.serializeValue = () => inputKey.value || ''
          localStorage.setItem('_mixlab_api_key', inputKey.value)
        })

        inputUrl.addEventListener('change', () => {
          api_url.serializeValue = () => inputUrl.value || ''
          localStorage.setItem('_mixlab_api_url', inputUrl.value)
        })

        /*
                Add the widget, make sure we clean up nicely, and we do not want to be serialized!
                */
        this.addCustomWidget(widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          inputUrl.remove()
          inputKey.remove()
          widget.div.remove()
          return onRemoved?.()
        }

        this.serialize_widgets = false
      }
    }
  }
})

app.registerExtension({
  name: 'Mixlab.GPT.SessionHistory',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeData.name === 'SessionHistory') {
      function populate (text) {
        if (this.widgets) {
          // const pos = this.widgets.findIndex((w) => w.name === "text");
          // if (pos !== -1) {
          // 	for (let i = pos; i < this.widgets.length; i++) {
          // 		this.widgets[i].onRemove?.();
          // 	}
          // 	this.widgets.length = pos;
          // }

          for (let i = 0; i < this.widgets.length; i++) {
            this.widgets[i].onRemove?.()
          }
          this.widgets.length = 0
        }

        console.log('SessionHistory', this.widgets, text)

        for (const list of text) {
          const w = ComfyWidgets['STRING'](
            this,
            'text',
            ['STRING', { multiline: true }],
            app
          ).widget
          w.inputEl.readOnly = true
          w.inputEl.style.opacity = 0.6

          let res = list

          try {
            res = JSON.stringify(JSON.parse(list), null, 2)
          } catch (error) {
            // console.log(list)
          }

          w.value = res
        }

        requestAnimationFrame(() => {
          const sz = this.computeSize()
          if (sz[0] < this.size[0]) {
            sz[0] = this.size[0]
          }
          if (sz[1] < this.size[1]) {
            sz[1] = this.size[1]
          }
          this.onResize?.(sz)
          app.graph.setDirtyCanvas(true, false)
        })
      }

      // When the node is executed we will be sent the input text, display this in the widget
      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        onExecuted?.apply(this, arguments)
        populate.call(this, message.text)
      }

      const onConfigure = nodeType.prototype.onConfigure
      nodeType.prototype.onConfigure = function () {
        onConfigure?.apply(this, arguments)
        if (this.widgets_values?.length) {
          populate.call(this, this.widgets_values)
        }
      }
    }
  }
})
