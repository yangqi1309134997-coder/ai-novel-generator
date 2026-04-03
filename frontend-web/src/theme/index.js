// 主题配置 -- 渐变紫色(#6366f1 -> #8b5cf6)
export const lightThemeOverrides = {
  common: {
    primaryColor: '#6366f1',
    primaryColorHover: '#818cf8',
    primaryColorPressed: '#4f46e5',
    primaryColorSuppl: '#a5b4fc',
    borderRadius: '12px',
    borderRadiusSmall: '8px',
    fontFamily:
      '"Inter", "Noto Sans SC", system-ui, -apple-system, sans-serif',
    fontSize: '14px',
    bodyColor: '#f8fafc',
    cardColor: '#ffffff',
    modalColor: '#ffffff',
    popoverColor: '#ffffff',
    tableColor: '#ffffff',
  },
  Button: {
    borderRadiusMedium: '10px',
    borderRadiusLarge: '12px',
    heightMedium: '40px',
    heightLarge: '48px',
    fontSizeMedium: '14px',
    fontSizeLarge: '16px',
  },
  Card: {
    borderRadius: '16px',
    paddingMedium: '24px',
  },
  Input: {
    borderRadius: '10px',
    heightMedium: '40px',
  },
  Menu: {
    borderRadius: '12px',
  },
  Tag: {
    borderRadius: '8px',
  },
}

export const darkThemeOverrides = {
  common: {
    primaryColor: '#818cf8',
    primaryColorHover: '#a5b4fc',
    primaryColorPressed: '#6366f1',
    primaryColorSuppl: '#c7d2fe',
    borderRadius: '12px',
    borderRadiusSmall: '8px',
    fontFamily:
      '"Inter", "Noto Sans SC", system-ui, -apple-system, sans-serif',
    fontSize: '14px',
    bodyColor: '#0f172a',
    cardColor: '#1e293b',
    modalColor: '#1e293b',
    popoverColor: '#1e293b',
    tableColor: '#1e293b',
    textColorBase: '#e2e8f0',
  },
  Button: {
    borderRadiusMedium: '10px',
    borderRadiusLarge: '12px',
    heightMedium: '40px',
    heightLarge: '48px',
  },
  Card: {
    borderRadius: '16px',
    color: '#1e293b',
    borderColor: '#334155',
  },
  Input: {
    borderRadius: '10px',
    color: '#1e293b',
    borderColor: '#334155',
  },
  Menu: {
    borderRadius: '12px',
  },
  Tag: {
    borderRadius: '8px',
  },
}
