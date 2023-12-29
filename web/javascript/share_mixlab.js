import { app } from '../../../scripts/app.js'
import { $el } from '../../../scripts/ui.js'
import { api } from '../../../scripts/api.js'

function get_position_style (ctx, widget_width, y, node_height) {
  const MARGIN = 12 // the margin around the html element

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
    flexDirection: 'row',
    // alignItems: 'center',
    justifyContent: 'flex-start'
  }
}

app.registerExtension({
  name: 'Mixlab.share.ShareToWeibo',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'ShareToWeibo') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)
        // console.log(this)
        const widget = {
          type: 'div',
          name: 'ShareToWeiboBtn',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(
                ctx,
                widget_width,
                node.widgets[2].last_y +16,
                node.size[1]
              )
            )
          }
        }

        const style = `
        flex-direction: row;
        background-color: var(--comfy-input-bg);
        border-radius: 8px;
        border-color: var(--border-color);
        border-style: solid;
        color: var(--descrip-text);`

        widget.div = $el('div', {})

        const btn = document.createElement('button')
        btn.innerText = 'Share'
        btn.style = style

        btn.addEventListener('click', () => {
          if (window._mixlab_share_to_weibo)
            window.open(window._mixlab_share_to_weibo)
        })

        document.body.appendChild(widget.div)
        widget.div.appendChild(btn)

        this.addCustomWidget(widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          widget.div.remove()
          return onRemoved?.()
        }

        this.serialize_widgets = true //需要保存参数
      }

      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = async function (message) {
        onExecuted?.apply(this, arguments)
        // console.log(this.widgets)

        window._mixlab_share_to_weibo = message.url
        try {
          const div = this.widgets.filter(w => w.div)[0].div
          Array.from(
            div.querySelectorAll('button'),
            b => (b.style.background = 'yellow')
          )
        } catch (error) {}
      }
    }
  }
})
