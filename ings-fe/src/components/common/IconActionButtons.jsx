import { FiEye, FiEdit2, FiTrash2 } from 'react-icons/fi'

/**
 * Boutons d'action icône seule (tooltip via title / aria-label).
 * Actions supportées : view | edit | delete | custom
 */
export default function IconActionButtons({ actions = [] }) {
  return (
    <div className="icon-action-group" role="group">
      {actions.map((action) => {
        if (!action || action.hidden) return null
        const {
          key,
          type = 'custom',
          onClick,
          title,
          disabled,
          href,
          className = '',
          icon: CustomIcon,
        } = action

        const Icon = CustomIcon
          || (type === 'view' ? FiEye : type === 'edit' ? FiEdit2 : type === 'delete' ? FiTrash2 : null)

        const label = title
          || (type === 'view' ? 'Voir' : type === 'edit' ? 'Modifier' : type === 'delete' ? 'Supprimer' : 'Action')

        const btnClass = [
          'btn',
          'btn-sm',
          'btn-icon-action',
          type === 'view' ? 'btn-outline-success' : '',
          type === 'edit' ? 'btn-outline-primary' : '',
          type === 'delete' ? 'btn-outline-danger' : '',
          className,
        ].filter(Boolean).join(' ')

        if (href) {
          return (
            <a
              key={key || label}
              href={href}
              className={btnClass}
              title={label}
              aria-label={label}
            >
              {Icon ? <Icon size={16} /> : label}
            </a>
          )
        }

        return (
          <button
            key={key || label}
            type="button"
            className={btnClass}
            title={label}
            aria-label={label}
            disabled={disabled}
            onClick={onClick}
          >
            {Icon ? <Icon size={16} /> : label}
          </button>
        )
      })}
    </div>
  )
}
